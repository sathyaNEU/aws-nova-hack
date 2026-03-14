"""
Slack Bolt app — listens for @mentions and DMs, routes to the Strands agent.

Run:
    python slack_app.py

Requirements in Slack app settings (api.slack.com/apps):
  - Socket Mode: ON
  - Bot Token Scopes: app_mentions:read, chat:write, im:history, im:read
  - Event Subscriptions: app_mention, message.im
"""
import os
import re
from dotenv import load_dotenv

load_dotenv()
print("[slack] Environment loaded")

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from agent.agent import handle_message

app = App(token=os.environ["SLACK_BOT_TOKEN"])
print("[slack] Slack Bolt app initialized")


# ── Helper ────────────────────────────────────────────────────────────────────

def _strip_mention(text: str) -> str:
    return re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip()


def _reply(client, channel: str, thread_ts: str, text: str):
    print(f"[slack] Sending reply to channel={channel} thread={thread_ts}: {text!r}")
    client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=text)


# ── Event handlers ────────────────────────────────────────────────────────────

@app.event("app_mention")
def on_mention(event, client, logger):
    print(f"[slack] app_mention event received: {event}")
    user_text = _strip_mention(event.get("text", ""))
    print(f"[slack] Stripped mention text: {user_text!r}")

    if not user_text:
        _reply(client, event["channel"], event["ts"], "Hi! How can I help? 👋")
        return

    response = handle_message(event["user"], user_text)
    _reply(client, event["channel"], event["ts"], response)


@app.event("message")
def on_dm(event, client, logger):
    print(f"[slack] message event received: {event}")

    if event.get("bot_id") or event.get("subtype"):
        print("[slack] Ignoring bot message or subtype event")
        return
    if event.get("channel_type") != "im":
        print(f"[slack] Ignoring non-DM message (channel_type={event.get('channel_type')})")
        return

    user_text = event.get("text", "").strip()
    print(f"[slack] DM text: {user_text!r}")

    if not user_text:
        return

    response = handle_message(event["user"], user_text)
    _reply(client, event["channel"], event["ts"], response)


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("[slack] Starting Slack agent (Socket Mode)…")
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()