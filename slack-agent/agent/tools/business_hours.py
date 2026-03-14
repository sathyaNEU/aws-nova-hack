"""
Tool: update_business_hours / get_business_hours
Updates or retrieves is_open, open_time, and/or close_time for a given day.
Database: PostgreSQL via psycopg2

Errors are raised as-is so they propagate back to Slack.
"""
import os
from typing import Optional
import psycopg2
from strands import tool


def _get_conn():
    print("[business_hours] Connecting to PostgreSQL…")
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    print("[business_hours] Connection established")
    return conn


def _format_time(t) -> str:
    """Format a time value (string or datetime.time) to 12-hour readable format."""
    if t is None:
        return "N/A"
    # psycopg2 may return datetime.time objects
    if hasattr(t, "strftime"):
        return t.strftime("%I:%M %p").lstrip("0")
    # Already a string like "09:00"
    from datetime import datetime
    try:
        return datetime.strptime(str(t), "%H:%M").strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return str(t)


def _row_to_summary(row: tuple) -> str:
    """Convert a DB row (day_of_week, is_open, open_time, close_time) to a readable line."""
    day, is_open, open_time, close_time = row
    status = "🟢 Open" if is_open else "🔴 Closed"
    if is_open and open_time and close_time:
        return f"*{day.capitalize()}*: {status} — {_format_time(open_time)} to {_format_time(close_time)}"
    return f"*{day.capitalize()}*: {status}"


DAY_ORDER = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


@tool
def get_business_hours(day_of_week: Optional[str] = None) -> str:
    """
    Retrieve business hours for a specific day or for the entire week.

    Use this when the user says things like:
      - "what are our hours?"
      - "show me the store hours"
      - "are we open on Sunday?"
      - "what time do we close on Friday?"
      - "show me today's hours"

    The caller (agent) is responsible for resolving relative terms like
    'today' or 'tomorrow' to a concrete day name before calling this tool.

    Args:
        day_of_week: One of: monday, tuesday, wednesday, thursday,
                     friday, saturday, sunday.
                     Omit (or pass None) to retrieve all 7 days.

    Returns:
        A formatted summary of the requested hours.
    """
    print(f"[business_hours] get_business_hours called — day={day_of_week!r}")

    with _get_conn() as conn:
        with conn.cursor() as cur:
            if day_of_week:
                day_of_week = day_of_week.strip().lower()
                valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
                if day_of_week not in valid_days:
                    raise ValueError(
                        f"Invalid day_of_week '{day_of_week}'. Must be one of: {', '.join(sorted(valid_days))}."
                    )
                cur.execute(
                    "SELECT day_of_week, is_open, open_time, close_time "
                    "FROM business_hours WHERE day_of_week = %s",
                    (day_of_week,),
                )
                row = cur.fetchone()
                if not row:
                    raise RuntimeError(
                        f"No row found for day_of_week='{day_of_week}' in business_hours. "
                        "Make sure the table is seeded with all 7 days."
                    )
                result = _row_to_summary(row)
            else:
                cur.execute(
                    "SELECT day_of_week, is_open, open_time, close_time FROM business_hours"
                )
                rows = cur.fetchall()
                if not rows:
                    raise RuntimeError("No rows found in business_hours table.")

                # Sort by day of week (Mon → Sun)
                rows_sorted = sorted(rows, key=lambda r: DAY_ORDER.index(r[0].lower()) if r[0].lower() in DAY_ORDER else 99)
                lines = [_row_to_summary(r) for r in rows_sorted]
                result = "📅 *Store Hours:*\n" + "\n".join(lines)

    print(f"[business_hours] Done — {result}")
    return result


@tool
def update_business_hours(
    day_of_week: str,
    is_open: Optional[bool] = None,
    open_time: Optional[str] = None,
    close_time: Optional[str] = None,
) -> str:
    """
    Update business hours for a specific day. Any combination of is_open,
    open_time, and close_time can be updated in a single call.

    Use this when the user says things like:
      - "the store is closed today"
      - "change Monday open time to 8am"
      - "Friday closes at 10pm"
      - "set Saturday hours to 9am - 6pm"
      - "we're open on Sunday from 11am to 5pm"

    The caller (agent) is responsible for resolving relative terms like
    'today' or 'tomorrow' to a concrete day name before calling this tool.

    Time format: 24-hour "HH:MM" (e.g. "09:00", "21:30"). Convert
    any 12-hour input (e.g. "9am", "9:30pm") to 24-hour before calling.

    Args:
        day_of_week: One of: monday, tuesday, wednesday, thursday,
                     friday, saturday, sunday.
        is_open:     True if open, False if closed. Omit if not changing.
        open_time:   Opening time in "HH:MM" format. Omit if not changing.
        close_time:  Closing time in "HH:MM" format. Omit if not changing.

    Returns:
        A confirmation message describing what was updated.
    """
    print(f"[business_hours] update_business_hours called — day={day_of_week!r}, is_open={is_open}, open_time={open_time!r}, close_time={close_time!r}")

    day_of_week = day_of_week.strip().lower()
    valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
    if day_of_week not in valid_days:
        raise ValueError(
            f"Invalid day_of_week '{day_of_week}'. Must be one of: {', '.join(sorted(valid_days))}."
        )

    if is_open is None and open_time is None and close_time is None:
        raise ValueError("Nothing to update — provide at least one of: is_open, open_time, close_time.")

    # Build SET clause dynamically from only the fields provided
    fields, values = [], []
    if is_open is not None:
        fields.append("is_open = %s")
        values.append(is_open)
    if open_time is not None:
        fields.append("open_time = %s")
        values.append(open_time)
    if close_time is not None:
        fields.append("close_time = %s")
        values.append(close_time)

    values.append(day_of_week)
    sql = f"UPDATE business_hours SET {', '.join(fields)} WHERE day_of_week = %s"
    print(f"[business_hours] SQL: {sql} | values: {values}")

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, values)
            print(f"[business_hours] Rows affected: {cur.rowcount}")
            if cur.rowcount == 0:
                raise RuntimeError(
                    f"No row found for day_of_week='{day_of_week}' in business_hours. "
                    "Make sure the table is seeded with all 7 days."
                )

    # Build a human-readable summary of what changed
    changes = []
    if is_open is not None:
        changes.append(f"status → {'open 🟢' if is_open else 'closed 🔴'}")
    if open_time is not None:
        changes.append(f"opens at {open_time}")
    if close_time is not None:
        changes.append(f"closes at {close_time}")

    result = f"✅ Updated *{day_of_week.capitalize()}*: {', '.join(changes)}."
    print(f"[business_hours] Done — {result}")
    return result