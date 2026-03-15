import asyncio
import base64
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

from aws_sdk_bedrock_runtime.client import (
    BedrockRuntimeClient,
    InvokeModelWithBidirectionalStreamOperationInput,
)
from aws_sdk_bedrock_runtime.models import (
    InvokeModelWithBidirectionalStreamInputChunk,
    BidirectionalInputPayloadPart,
)
from aws_sdk_bedrock_runtime.config import Config, HTTPAuthSchemeResolver, SigV4AuthScheme
from smithy_aws_core.identity import EnvironmentCredentialsResolver

from mcp_client import MCPClient

NOVA_INPUT_RATE = 16_000
NOVA_OUTPUT_RATE = 24_000

_TODAY = datetime.now(timezone.utc).date()
_TOMORROW = _TODAY + timedelta(days=1)
_TODAY_STR = f"{_TODAY.isoformat()}, {_TODAY.strftime('%A')}"
_TOMORROW_STR = f"{_TOMORROW.isoformat()}, {_TOMORROW.strftime('%A')}"

SYSTEM_PROMPT = f"""
You are the voice receptionist for Nova Dine, an Italian restaurant in Brooklyn, NY.
You sound like a real, warm human host — use natural filler sounds like "hmm", "sure", "of course",
"let me check that for you" — but stay concise. Never ramble.

When the conversation starts, you MUST greet the caller with exactly this message:
"Thank you for calling Nova Dine! How can I help you today?"
Do not paraphrase or change this greeting. Say it word for word every time.

Today's date is {_TODAY_STR}.
Tomorrow's date is {_TOMORROW_STR}.
Always use these dates as the base when a caller says "tomorrow", "this Friday", "next week", etc.
When building a datetime string for a tool call, ALWAYS format it as "YYYY-MM-DD HH:MM" in a single field.
Example: "2025-03-14 18:30". Never split date and time into separate keys. Never guess or invent a date.

Your responsibilities:
- Take and cancel table reservations
- Place takeout / pickup orders
- Answer questions about the menu, prices, dietary needs, allergens, hours, location, and parking

STRICT RULES — follow these without exception:

1. DO NOT ask any question that is not directly required to fill a tool's parameters.
   For create_reservation you need: customer name, party size, date + time, phone number.
   Ask only for what is still missing. Never ask "is there anything else?" or small-talk questions.

2. If a caller asks ANYTHING you do not have concrete information about — menu items, prices,
   specials, hours, policies, wait times, or anything else — do NOT guess or assume.
   Say exactly: "Hmm, I don't have that information on hand. Let me get the manager to reach out
   to you — could I get your name and phone number?" Then call escalate_to_manager immediately.

3. If the caller is frustrated, upset, or asks for a human, say:
   "Of course, connecting you now." Then call transfer_call with the active CallSid.
   Do NOT call escalate_to_manager in this case.

4. RESPONSE LENGTH — this is a phone call, not a menu reading. Hard limits:
   - Maximum 2 sentences per response in normal conversation.
   - When listing menu items: say the NAME and PRICE only. No descriptions, no dietary tags
     unless the caller explicitly asks. Maximum 3 items per response.
     If there are more items, say "and a few more — want me to keep going?"
   - When listing parking/location/hours info: give the single most useful fact first,
     then stop. Do not read out every option unprompted.
   - Never use bullet points, headers, or markdown formatting — this is spoken audio.

5. Always confirm key details back to the caller before calling any tool.
   Example: "Got it — table for 3, tomorrow at 7 PM under Sarah, and I can reach you at 555-1234.
   Let me lock that in for you."
""".strip()


class NovaSonic:
    def __init__(self, mcp: MCPClient, model_id: str = "amazon.nova-2-sonic-v1:0"):
        self.model_id = model_id
        self.region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.mcp = mcp

        self.client = None
        self.stream = None
        self.response_task = None
        self.is_active = False

        self.prompt_name = str(uuid.uuid4())
        self.content_name = str(uuid.uuid4())
        self.audio_content_name = str(uuid.uuid4())

        self.audio_queue = asyncio.Queue()

        self.twilio_resample_state = None
        self._audio_buffer = bytearray()
        self._audio_buffer_ms = 0
        self.CHUNK_MS = 100

        self._role = None
        self._current_content_type = None
        self._display_assistant_text = False

        self._in_tool_use = False
        self._tool_use_id = None
        self._tool_name = None
        self._tool_input = {}

        # Gate: block audio relay until Twilio stream connects
        self._ready_for_audio = asyncio.Event()

        # ── Barge-in state ────────────────────────────────────────────────────
        self._nova_speaking = False
        self._generation_id = 0
        self._barge_in_fired = False
        self._barge_in_lock = asyncio.Lock()

        # ── NEW: event that main.py watches to send Twilio 'clear' ───────────
        self.barge_in_event = asyncio.Event()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_client(self):
        config = Config(
            endpoint_uri=f"https://bedrock-runtime.{self.region}.amazonaws.com",
            region=self.region,
            aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
            auth_scheme_resolver=HTTPAuthSchemeResolver(),
            auth_schemes={"aws.auth#sigv4": SigV4AuthScheme(service="bedrock")},
        )
        self.client = BedrockRuntimeClient(config=config)

    async def _send(self, payload: dict):
        raw = json.dumps(payload)
        chunk = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=raw.encode("utf-8"))
        )
        await self.stream.input_stream.send(chunk)

    def _clear_audio_queue_nowait(self) -> int:
        cleared = 0
        while True:
            try:
                self.audio_queue.get_nowait()
                cleared += 1
            except asyncio.QueueEmpty:
                break
        return cleared

    # ── Barge-in handler ──────────────────────────────────────────────────────

    async def _handle_barge_in(self, reason: str):
        async with self._barge_in_lock:
            if self._barge_in_fired:
                return

            self._barge_in_fired = True
            self._nova_speaking = False
            self._generation_id += 1
            cleared = self._clear_audio_queue_nowait()
            print(f"[nova] Barge-in ({reason}) — gen={self._generation_id}, cleared {cleared} chunks")

            # Signal main.py to send Twilio 'clear' and flush Twilio's playback buffer
            self.barge_in_event.set()

            try:
                await self._close_audio_channel()
                await self._open_audio_channel()
            except Exception as e:
                print(f"[nova] Audio channel cycle error: {e}")

    # ── Audio channel helpers ─────────────────────────────────────────────────

    async def _close_audio_channel(self):
        try:
            await self._send({
                "event": {
                    "contentEnd": {
                        "promptName": self.prompt_name,
                        "contentName": self.audio_content_name,
                    }
                }
            })
        except Exception as e:
            print(f"[nova] _close_audio_channel error: {e}")

    async def _open_audio_channel(self):
        self.audio_content_name = str(uuid.uuid4())
        await self._send({
            "event": {
                "contentStart": {
                    "promptName": self.prompt_name,
                    "contentName": self.audio_content_name,
                    "type": "AUDIO",
                    "interactive": True,
                    "role": "USER",
                    "audioInputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": NOVA_INPUT_RATE,
                        "sampleSizeBits": 16,
                        "channelCount": 1,
                        "audioType": "SPEECH",
                        "encoding": "base64",
                    },
                }
            }
        })
        print(f"[nova] Audio channel opened (name={self.audio_content_name})")

    async def _send_audio_bytes(self, pcm_bytes: bytes):
        payload = base64.b64encode(pcm_bytes).decode("utf-8")
        await self._send({
            "event": {
                "audioInput": {
                    "promptName": self.prompt_name,
                    "contentName": self.audio_content_name,
                    "content": payload,
                }
            }
        })

    # ── Session lifecycle ─────────────────────────────────────────────────────

    async def start_session(self):
        if not self.client:
            self._build_client()

        self.stream = await self.client.invoke_model_with_bidirectional_stream(
            InvokeModelWithBidirectionalStreamOperationInput(model_id=self.model_id)
        )
        self.is_active = True

        await self._send({
            "event": {
                "sessionStart": {
                    "inferenceConfiguration": {
                        "maxTokens": 1024,
                        "topP": 0.9,
                        "temperature": 0.7,
                    },
                    "turnDetectionConfiguration": {
                        "endpointingSensitivity": "HIGH"
                    },
                }
            }
        })

        tool_schemas = self.mcp.list_tool_schemas()
        prompt_start_payload = {
            "promptName": self.prompt_name,
            "textOutputConfiguration": {"mediaType": "text/plain"},
            "audioOutputConfiguration": {
                "mediaType": "audio/lpcm",
                "sampleRateHertz": NOVA_OUTPUT_RATE,
                "sampleSizeBits": 16,
                "channelCount": 1,
                "voiceId": "matthew",
                "encoding": "base64",
                "audioType": "SPEECH",
            },
        }
        if tool_schemas:
            prompt_start_payload["toolUseOutputConfiguration"] = {"mediaType": "application/json"}
            prompt_start_payload["toolConfiguration"] = {
                "tools": tool_schemas,
                "toolChoice": {"auto": {}},
            }

        await self._send({"event": {"promptStart": prompt_start_payload}})

        # System prompt
        await self._send({
            "event": {
                "contentStart": {
                    "promptName": self.prompt_name,
                    "contentName": self.content_name,
                    "type": "TEXT",
                    "interactive": False,
                    "role": "SYSTEM",
                    "textInputConfiguration": {"mediaType": "text/plain"},
                }
            }
        })
        await self._send({
            "event": {
                "textInput": {
                    "promptName": self.prompt_name,
                    "contentName": self.content_name,
                    "content": SYSTEM_PROMPT,
                }
            }
        })
        await self._send({
            "event": {
                "contentEnd": {
                    "promptName": self.prompt_name,
                    "contentName": self.content_name,
                }
            }
        })

        # Open persistent audio channel BEFORE greeting so Nova can listen after
        await self._open_audio_channel()

        # ── Trigger greeting ──────────────────────────────────────────────────
        greeting_name = str(uuid.uuid4())
        await self._send({
            "event": {
                "contentStart": {
                    "promptName": self.prompt_name,
                    "contentName": greeting_name,
                    "type": "TEXT",
                    "interactive": True,
                    "role": "USER",
                    "textInputConfiguration": {"mediaType": "text/plain"},
                }
            }
        })
        await self._send({
            "event": {
                "textInput": {
                    "promptName": self.prompt_name,
                    "contentName": greeting_name,
                    "content": "[conversation started]",
                }
            }
        })
        await self._send({
            "event": {
                "contentEnd": {
                    "promptName": self.prompt_name,
                    "contentName": greeting_name,
                }
            }
        })

        print("[nova] Session setup complete — starting response processor")
        self.response_task = asyncio.create_task(self._process_responses())

    async def start_audio_input(self, call_sid: str = ""):
        self._call_sid = call_sid
        print("[nova] Twilio audio stream connected — ready to receive caller audio")
        self._ready_for_audio.set()

        # Inject the CallSid as a late USER message so Nova can pass it to transfer_call
        if call_sid:
            name = str(uuid.uuid4())
            await self._send({
                "event": {
                    "contentStart": {
                        "promptName": self.prompt_name,
                        "contentName": name,
                        "type": "TEXT",
                        "interactive": False,
                        "role": "USER",
                        "textInputConfiguration": {"mediaType": "text/plain"},
                    }
                }
            })
            await self._send({
                "event": {
                    "textInput": {
                        "promptName": self.prompt_name,
                        "contentName": name,
                        "content": f"[system] The active Twilio CallSid is: {call_sid}",
                    }
                }
            })
            await self._send({
                "event": {
                    "contentEnd": {
                        "promptName": self.prompt_name,
                        "contentName": name,
                    }
                }
            })
            print(f"[nova] Injected CallSid: {call_sid}")

    async def send_audio_chunk(self, pcm_bytes: bytes):
        if not self.is_active:
            return

        self._audio_buffer.extend(pcm_bytes)
        self._audio_buffer_ms += len(pcm_bytes) // 32

        if self._audio_buffer_ms >= self.CHUNK_MS:
            chunk = bytes(self._audio_buffer)
            self._audio_buffer = bytearray()
            self._audio_buffer_ms = 0

            if self._ready_for_audio.is_set():
                await self._send_audio_bytes(chunk)

    async def end_audio_input(self):
        await self._close_audio_channel()

    async def end_session(self):
        if not self.is_active:
            return
        self.is_active = False
        try:
            await self._send({"event": {"promptEnd": {"promptName": self.prompt_name}}})
            await self._send({"event": {"sessionEnd": {}}})
            await self.stream.input_stream.close()
        except Exception:
            pass
        if self.response_task:
            self.response_task.cancel()

    # ── Tool result sender ────────────────────────────────────────────────────

    async def _send_tool_result(self, tool_use_id: str, result_content: str):
        content_name = str(uuid.uuid4())
        await self._send({
            "event": {
                "contentStart": {
                    "promptName": self.prompt_name,
                    "contentName": content_name,
                    "interactive": False,
                    "type": "TOOL",
                    "role": "USER",
                    "toolResultInputConfiguration": {
                        "toolUseId": tool_use_id,
                        "type": "TEXT",
                        "textInputConfiguration": {
                            "mediaType": "text/plain"
                        },
                    },
                }
            }
        })
        await self._send({
            "event": {
                "toolResult": {
                    "promptName": self.prompt_name,
                    "contentName": content_name,
                    "content": result_content,
                }
            }
        })
        await self._send({
            "event": {
                "contentEnd": {
                    "promptName": self.prompt_name,
                    "contentName": content_name,
                }
            }
        })

    # ── Response processor ────────────────────────────────────────────────────

    async def _process_responses(self):
        current_content_type = None
        current_stage = ""

        try:
            while self.is_active:
                output = await self.stream.await_output()
                result = await output[1].receive()

                if not (result.value and result.value.bytes_):
                    print("[nova rx] empty frame")
                    continue

                data = json.loads(result.value.bytes_.decode("utf-8"))
                event = data.get("event", {})

                if event:
                    keys = list(event.keys())
                    if keys not in (["audioOutput"], ["textOutput"]):
                        print(f"[nova rx] event keys: {keys}")

                # ── top-level interrupted signal ──────────────────────────────
                if "interrupted" in event:
                    await self._handle_barge_in("interrupted-toplevel")
                    continue

                if "contentStart" in event:
                    cs = event["contentStart"]
                    self._role = cs.get("role")
                    current_content_type = cs.get("type")

                    add_fields = cs.get("additionalModelFields")
                    current_stage = (
                        json.loads(add_fields).get("generationStage", "")
                        if add_fields else ""
                    )
                    print(f"[nova rx] contentStart role={self._role} type={current_content_type} stage={current_stage}")

                    # ── KEY FIX: FINAL TEXT after audio = Nova's "I finished
                    #    speaking" marker. This is NOT a barge-in signal — it
                    #    means Nova completed naturally. Reset state. ──────────
                    if self._role == "ASSISTANT" and current_content_type == "TEXT" and current_stage == "FINAL":
                        self._nova_speaking = False
                        self._barge_in_fired = False
                        print("[nova] Turn complete — barge-in re-armed")
                        # consume the empty contentEnd that follows and move on
                        continue

                    # ── USER contentStart while Nova is speaking = real barge-in
                    if self._role == "USER" and self._nova_speaking:
                        await self._handle_barge_in("user-started-speaking")

                    elif self._role == "ASSISTANT":
                        self._barge_in_fired = False

                    if current_content_type == "TOOL":
                        self._in_tool_use = True
                        self._tool_input = {}
                        tool_use = (
                            cs.get("toolUseContent")
                            or cs.get("toolUse")
                            or cs
                        )
                        self._tool_use_id = (
                            tool_use.get("toolUseId")
                            or tool_use.get("toolInvocationId")
                            or cs.get("toolUseId")
                            or cs.get("toolInvocationId")
                        )
                        self._tool_name = (
                            tool_use.get("toolName")
                            or tool_use.get("name")
                            or cs.get("toolName")
                            or cs.get("name")
                        )
                        print(f"[tool] Bedrock wants to call → {self._tool_name} (id={self._tool_use_id})")
                    else:
                        self._in_tool_use = False
                        if current_content_type == "TEXT":
                            self._display_assistant_text = (current_stage == "SPECULATIVE")

                elif "toolUse" in event:
                    tu = event["toolUse"]
                    if not self._tool_use_id:
                        self._tool_use_id = tu.get("toolUseId") or tu.get("toolInvocationId")
                    if not self._tool_name:
                        self._tool_name = tu.get("toolName") or tu.get("name")
                    raw_input = tu.get("content", "{}")
                    try:
                        self._tool_input = json.loads(raw_input)
                    except json.JSONDecodeError:
                        self._tool_input = {"raw": raw_input}

                elif "contentEnd" in event:
                    if self._in_tool_use:
                        self._in_tool_use = False
                        tool_use_id = self._tool_use_id
                        tool_name = self._tool_name
                        tool_input = self._tool_input

                        print(f"[tool] Calling {tool_name} with {tool_input}")
                        try:
                            result_str = await self.mcp.call_tool(tool_name, tool_input)
                        except Exception as e:
                            result_str = json.dumps({"error": str(e)})

                        print(f"[tool] Result for {tool_name}: {result_str}")
                        await self._send_tool_result(tool_use_id, result_str)

                    elif self._role == "ASSISTANT" and current_content_type == "AUDIO":
                        print("[nova] AUDIO block ended")
                        if not self._ready_for_audio.is_set():
                            print("[nova] Greeting audio done — opening caller audio gate")
                            self._ready_for_audio.set()
                        # Nova finished speaking naturally — mark as done
                        self._nova_speaking = False

                    current_content_type = None
                    current_stage = ""

                elif "textOutput" in event:
                    text = event["textOutput"]["content"]

                    # ── Nova Sonic inline interrupted signal ──────────────────
                    if '{ "interrupted" : true }' in text:
                        await self._handle_barge_in("interrupted-text-signal")
                        continue

                    if self._role == "ASSISTANT" and self._display_assistant_text:
                        print(f"[Assistant] {text}")
                    elif self._role == "USER":
                        print(f"[User]      {text}")

                elif "audioOutput" in event:
                    if self._barge_in_fired:
                        continue

                    audio_bytes = base64.b64decode(event["audioOutput"]["content"])

                    if not self._nova_speaking:
                        self._nova_speaking = True
                        print("[nova] Nova started speaking")

                    await self.audio_queue.put((self._generation_id, audio_bytes))

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[nova response error] {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raw = getattr(e, "body", None) or getattr(e, "message", None)
            if raw:
                print(f"[nova response error] raw payload: {raw}")