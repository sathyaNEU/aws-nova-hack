"""
tools/reservations.py

create_reservation now validates against live business_hours from master_data
before writing to RDS. The check is intentionally strict:
  - Closed day → rejected
  - Reservation time outside open_time…close_time window → rejected
"""

import datetime as datetime_module
import logging
import os
import uuid

from mcp.server.fastmcp import FastMCP

from data.master_data import master_data
from utils.slack.actions import post_message
from utils.rds.reservations.core import insert_reservation, update_reservation_status

logger = logging.getLogger(__name__)

# Day-of-week index used by datetime.weekday()
_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _is_within_hours(parsed_dt: datetime_module.datetime) -> tuple[bool, str]:
    """
    Check whether `parsed_dt` falls within the restaurant's operating window
    for that day of the week.

    Returns (ok: bool, reason: str).
    """
    hours = master_data.get("business_hours", {})
    if not hours:
        # No hours loaded — fail open so we don't silently block reservations
        logger.warning("[reservations] business_hours not loaded; skipping hours check")
        return True, ""

    day_name = _WEEKDAYS[parsed_dt.weekday()]
    day_info  = hours.get(day_name)

    if day_info is None:
        logger.warning("[reservations] No hours entry for %s; skipping check", day_name)
        return True, ""

    if not day_info.get("is_open"):
        return False, f"Sorry, we're closed on {day_name.capitalize()}s."

    open_str  = day_info.get("open_time")
    close_str = day_info.get("close_time")

    if not open_str or not close_str:
        return True, ""  # incomplete data — fail open

    open_t  = datetime_module.time.fromisoformat(open_str)   # "HH:MM" → time
    close_t = datetime_module.time.fromisoformat(close_str)
    res_t   = parsed_dt.time()

    if not (open_t <= res_t <= close_t):
        return (
            False,
            f"Sorry, we're open {open_str}–{close_str} on {day_name.capitalize()}s. "
            f"Your requested time ({res_t.strftime('%H:%M')}) is outside that window.",
        )

    return True, ""


def register(mcp: FastMCP):

    @mcp.tool()
    def create_reservation(
        customer_name: str,
        party_size: int,
        datetime: str,
        phone: str,
        special_requests: str = "",
    ) -> dict:
        """
        Create a table reservation and return the confirmation payload.

        Parameters
        ----------
        customer_name    : Full name of the guest making the reservation.
        party_size       : Number of guests (1-8; parties >8 require manager approval).
        datetime         : Reservation date AND time as a single string in
                           "YYYY-MM-DD HH:MM" format (24-hour clock).
                           TODAY's date is injected automatically at runtime —
                           use it as the base when the caller says "tomorrow",
                           "this Friday", etc.
        phone            : Contact phone number for the reservation.
        special_requests : Any dietary needs, celebrations, seating preferences, etc.

        Returns a confirmation object with a reservation_id.
        """
        today = datetime_module.datetime.now(datetime_module.timezone.utc).date()

        # ── Validate datetime format ──────────────────────────────────────────
        try:
            parsed_dt = datetime_module.datetime.strptime(datetime, "%Y-%m-%d %H:%M")
        except ValueError:
            return {
                "success": False,
                "error": (
                    f"Invalid datetime format '{datetime}'. "
                    f"Use 'YYYY-MM-DD HH:MM'. Today is {today.isoformat()}."
                ),
            }

        # ── Validate business hours ───────────────────────────────────────────
        ok, reason = _is_within_hours(parsed_dt)
        if not ok:
            return {"success": False, "error": reason}

        # ── Build confirmation ────────────────────────────────────────────────
        reservation_id = uuid.uuid4().hex[:8].upper()
        confirmation = {
            "success": True,
            "reservation_id": reservation_id,
            "restaurant": "Bella Tavola",
            "customer_name": customer_name,
            "party_size": party_size,
            "datetime": datetime,
            "phone": phone,
            "special_requests": special_requests or None,
            "status": "CONFIRMED",
            "hold_policy": "Reservation held for 15 minutes past booking time.",
            "cancellation_policy": "Free cancellation up to 24 hours before. Late fee: $15/person.",
            "created_at": _utcnow_iso(),
        }

        # ── Persist to RDS ────────────────────────────────────────────────────
        insert_reservation(
            reservation_id=reservation_id,
            customer_name=customer_name,
            party_size=party_size,
            datetime_str=datetime,
            phone=phone,
            special_requests=special_requests,
            status="CONFIRMED",
        )

        # ── Notify Slack ──────────────────────────────────────────────────────
        _notify_slack(confirmation)

        return confirmation

    @mcp.tool()
    def cancel_reservation(
        reservation_id: str,
        customer_name: str,
        phone: str,
    ) -> dict:
        """
        Cancel an existing reservation by its reservation_id.

        Parameters
        ----------
        reservation_id : The 8-character ID returned when the reservation was created.
        customer_name  : Name on the reservation (for verification).
        phone          : Phone number on the reservation (for verification).

        Returns a cancellation confirmation.
        """
        if not reservation_id or len(reservation_id) != 8:
            return {"success": False, "error": "Invalid reservation_id format."}

        updated = update_reservation_status(reservation_id, "CANCELLED")

        if not updated:
            return {
                "success": False,
                "error": (
                    f"Reservation '{reservation_id.upper()}' not found. "
                    "Please check the ID and try again."
                ),
            }

        result = {
            "success": True,
            "reservation_id": reservation_id.upper(),
            "status": "CANCELLED",
            "customer_name": customer_name,
            "phone": phone,
            "message": (
                f"Reservation {reservation_id.upper()} has been successfully cancelled. "
                "No cancellation fee applies if cancelled more than 24 hours in advance."
            ),
            "cancelled_at": _utcnow_iso(),
        }

        _notify_slack(result)
        return result


# ── Private helpers ───────────────────────────────────────────────────────────

def _utcnow_iso() -> str:
    return datetime_module.datetime.now(datetime_module.timezone.utc).isoformat()


def _notify_slack(payload: dict) -> None:
    channel = os.getenv("SLACK_RESERVATION_CHANNEL")
    if not channel:
        logger.warning("SLACK_RESERVATION_CHANNEL not set — skipping Slack notification.")
        return

    res_id = payload["reservation_id"]
    name   = payload["customer_name"]
    status = payload["status"]

    is_cancellation = status == "CANCELLED"

    if is_cancellation:
        header_text  = "❌ Reservation Cancelled — Bella Tavola"
        status_emoji = "❌"
        fallback     = f"❌ Reservation cancelled at Bella Tavola — {name} [{res_id}]"
    else:
        header_text  = "🍽️ New Reservation — Bella Tavola"
        status_emoji = "✅"
        fallback     = (
            f"📅 New reservation at Bella Tavola — "
            f"{name}, party of {payload.get('party_size')} on {payload.get('datetime')} [{res_id}]"
        )

    fields = [
        {"type": "mrkdwn", "text": f"*Reservation ID:*\n`{res_id}`"},
        {"type": "mrkdwn", "text": f"*Status:*\n{status_emoji} {status}"},
        {"type": "mrkdwn", "text": f"*Guest:*\n{name}"},
        {"type": "mrkdwn", "text": f"*Phone:*\n{payload['phone']}"},
    ]

    if not is_cancellation:
        fields += [
            {"type": "mrkdwn", "text": f"*Party size:*\n{payload.get('party_size')}"},
            {"type": "mrkdwn", "text": f"*Date & Time:*\n{payload.get('datetime')}"},
            {"type": "mrkdwn", "text": f"*Special requests:*\n{payload.get('special_requests') or '—'}"},
        ]

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": header_text}},
        {"type": "section", "fields": fields},
        {"type": "divider"},
    ]

    if not is_cancellation:
        blocks.append({
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"⏱ {payload.get('hold_policy', '')}"},
                {"type": "mrkdwn", "text": f"🚫 {payload.get('cancellation_policy', '')}"},
            ],
        })

    try:
        result = post_message(channel=channel, text=fallback, blocks=blocks)
        if not result.get("ok"):
            logger.error("Slack notification failed: %s", result.get("error"))
    except Exception:
        logger.exception("Unexpected error while sending Slack reservation notification.")