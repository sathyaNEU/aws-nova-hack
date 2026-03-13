"""
utils/rds/business_hours/core.py

PostgreSQL operations for the business_hours table.

Schema:
  business_hours
    day_of_week  VARCHAR  PRIMARY KEY   -- 'monday' … 'sunday'
    is_open      BOOLEAN  NOT NULL
    open_time    TIME / VARCHAR          -- '11:00'
    close_time   TIME / VARCHAR          -- '22:00'
"""

import logging
import os

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


# ── Connection ────────────────────────────────────────────────────────────────

def _get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_hhmm(value) -> str | None:
    """Normalise a DB time value to 'HH:MM' string, or None if absent."""
    if value is None:
        return None
    if hasattr(value, "strftime"):      # datetime.time object
        return value.strftime("%H:%M")
    return str(value)[:5]               # already a string like '09:00:00'


# ── Read ──────────────────────────────────────────────────────────────────────

def fetch_all_business_hours() -> dict:
    """
    Fetch all rows from business_hours and return a dict keyed by day_of_week.

    Example return value:
      {
        "monday":    {"is_open": True,  "open_time": "11:00", "close_time": "22:00"},
        "tuesday":   {"is_open": True,  "open_time": "11:00", "close_time": "22:00"},
        "sunday":    {"is_open": False, "open_time": None,    "close_time": None},
        ...
      }
    """
    sql = "SELECT day_of_week, is_open, open_time, close_time FROM business_hours;"
    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchall()
        result = {}
        for r in rows:
            day = r["day_of_week"].strip().lower()
            result[day] = {
                "is_open":    r["is_open"],
                "open_time":  _to_hhmm(r["open_time"]),
                "close_time": _to_hhmm(r["close_time"]),
            }
        logger.info("[rds] Fetched business_hours for %d days", len(result))
        return result
    except Exception:
        logger.exception("[rds] Failed to fetch business_hours")
        return {}