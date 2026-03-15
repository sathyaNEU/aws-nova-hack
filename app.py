import asyncio
import base64
import json

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, Request, HTTPException
from fastapi.responses import Response
import uvicorn
from dotenv import load_dotenv

from nova_sonic import NovaSonic
from mcp_client import MCPClient
from utils.audio import twilio_to_nova, nova_to_twilio
from utils.slack.actions import verify_slack_signature, ACTION_HANDLERS

load_dotenv()

mcp = MCPClient(server_script="mcp_server.py")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await mcp.start()
    yield
    await mcp.stop()


app = FastAPI(lifespan=lifespan)


# ── Slack interactivity route ─────────────────────────────────────────────────

@app.post("/slack/actions")
async def slack_actions(request: Request):
    body = await request.body()

    if not verify_slack_signature(body, dict(request.headers)):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    form = await request.form()
    payload = json.loads(form["payload"])

    if payload.get("type") != "block_actions":
        return {"ok": True}

    action = payload["actions"][0]
    channel = payload["container"]["channel_id"]
    msg_ts = payload["container"]["message_ts"]
    manager = payload["user"]["name"]

    handler = ACTION_HANDLERS.get(action["action_id"])
    if handler:
        handler(json.loads(action.get("value", "{}")), channel, msg_ts, manager)

    return {"ok": True}


@app.get("/")
async def health_check():
    return {"status": "ok"}


# ── TwiML endpoint ────────────────────────────────────────────────────────────

@app.post("/incoming-call")
async def incoming_call(request: Request):
    host = request.headers.get("host", "")
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://{host}/media-stream" />
  </Connect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")


# ── WebSocket media stream ────────────────────────────────────────────────────

@app.websocket("/media-stream")
async def media_stream(ws: WebSocket):
    await ws.accept()
    print("[ws] Twilio connected")

    nova = NovaSonic(mcp=mcp)
    send_task = asyncio.create_task(_noop())
    stream_sid: str | None = None

    await nova.start_session()

    # ── Background task: watches for barge-in and sends Twilio 'clear' ────────
    async def _watch_barge_in():
        while nova.is_active:
            await nova.barge_in_event.wait()   # blocks until barge-in fires
            nova.barge_in_event.clear()
            if stream_sid:
                try:
                    await ws.send_text(json.dumps({
                        "event": "clear",
                        "streamSid": stream_sid,
                    }))
                    print("[ws] Sent Twilio 'clear' to flush playback buffer")
                except Exception as e:
                    print(f"[ws] clear send error: {e}")

    barge_in_watcher = asyncio.create_task(_watch_barge_in())

    try:
        async for raw in ws.iter_text():
            msg = json.loads(raw)
            event = msg.get("event")

            if event == "start":
                stream_sid = msg["start"]["streamSid"]
                call_sid   = msg["start"]["callSid"]
                print(f"[ws] Stream started: {stream_sid}")
                await nova.start_audio_input(call_sid=call_sid)

                send_task.cancel()
                send_task = asyncio.create_task(
                    _relay_nova_to_twilio(ws, nova, stream_sid)
                )

            elif event == "media":
                mulaw = base64.b64decode(msg["media"]["payload"])
                pcm, nova.twilio_resample_state = twilio_to_nova(
                    mulaw, nova.twilio_resample_state
                )
                await nova.send_audio_chunk(pcm)

            elif event == "stop":
                print("[ws] Stream stopped")
                break

    except Exception as e:
        print(f"[ws error] {e}")
    finally:
        nova.is_active = False
        send_task.cancel()
        barge_in_watcher.cancel()
        await nova.end_session()
        print("[ws] Session cleaned up")


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _relay_nova_to_twilio(ws: WebSocket, nova: NovaSonic, stream_sid: str):
    resample_state = None
    try:
        while nova.is_active:
            item = await nova.audio_queue.get()
            gen_id, pcm_24k = item

            # Drop stale chunks from before the barge-in
            if gen_id != nova._generation_id:
                continue

            mulaw, resample_state = nova_to_twilio(pcm_24k, resample_state)
            await ws.send_text(json.dumps({
                "event": "media",
                "streamSid": stream_sid,
                "media": {"payload": base64.b64encode(mulaw).decode("utf-8")},
            }))
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[relay error] {e}")


async def _noop():
    await asyncio.sleep(0)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)