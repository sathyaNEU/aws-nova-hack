import hashlib
import hmac
import json
import os
import time

import httpx

from utils.pos.square import SquarePOS


# ── Signature verification ────────────────────────────────────────────────────

def verify_slack_signature(body: bytes, headers: dict) -> bool:
    signing_secret = os.getenv("SLACK_SIGNING_SECRET", "")
    ts        = headers.get("x-slack-request-timestamp", "")
    signature = headers.get("x-slack-signature", "")
    if not ts or not signature or not signing_secret:
        return False
    if abs(time.time() - int(ts)) > 300:
        return False
    base_str = f"v0:{ts}:{body.decode()}"
    expected = "v0=" + hmac.new(
        signing_secret.encode(),
        base_str.encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── Slack API helpers ─────────────────────────────────────────────────────────

def post_message(channel: str, text: str, blocks: list | None = None) -> dict:
    """
    Post a new message to a Slack channel.

    Parameters
    ----------
    channel : Channel ID or name (e.g. os.getenv('SLACK_RESERVATION_CHANNEL')).
    text    : Fallback plain-text content (used in notifications / accessibility).
    blocks  : Optional Block Kit payload. When omitted a simple mrkdwn section is used.

    Returns the parsed Slack API response dict.
    """
    payload = {
        "channel": channel,
        "text": text,
        "blocks": blocks or [
            {"type": "section", "text": {"type": "mrkdwn", "text": text}}
        ],
    }
    response = httpx.post(
        "https://slack.com/api/chat.postMessage",
        headers={
            "Authorization": f"Bearer {os.getenv('SLACK_BOT_TOKEN')}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=10.0,
    )
    return response.json()


def update_message(channel: str, ts: str, text: str):
    httpx.post(
        "https://slack.com/api/chat.update",
        headers={
            "Authorization": f"Bearer {os.getenv('SLACK_BOT_TOKEN')}",
            "Content-Type": "application/json",
        },
        json={
            "channel": channel,
            "ts": ts,
            "text": text,
            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": text}}],
        },
        timeout=10.0,
    )


# ── Action handlers ───────────────────────────────────────────────────────────

def handle_issue_refund(value: dict, channel: str, ts: str, manager: str):
    order_number = value["order_number"]
    contact_name = value["contact_name"]
    phone        = value["phone"]
    try:
        result = SquarePOS().refund_order(pos_order_id=order_number)
    except Exception as exc:
        update_message(channel, ts, f"❌ Refund failed for order {order_number}: {exc}")
        return
    if result.get("success"):
        update_message(channel, ts, f"✅ Refund issued for order *{order_number}* ({contact_name}, {phone}) by {manager}.")
    else:
        update_message(channel, ts, f"❌ Refund failed for order *{order_number}*: {result.get('error')}")


def handle_mark_completed(value: dict, channel: str, ts: str, manager: str):
    msg = (
        f"✔ *Escalation marked as completed* by *{manager}*\n\n"
        f"*Received payload details:*\n"
        f">*Customer:* {value.get('contact_name', 'N/A')}\n"
        f">*Phone:* {value.get('phone', 'N/A')}\n"
        f">*Order #:* {value.get('order_number', 'N/A')}\n"
        f">*Issue:* {value.get('issue', 'N/A')}"
    )
    update_message(channel, ts, msg)


ACTION_HANDLERS = {
    "issue_refund":    handle_issue_refund,
    "mark_completed":  handle_mark_completed,
}