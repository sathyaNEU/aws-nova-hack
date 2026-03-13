"""
utils/rds/reservations/core.py

Handles all PostgreSQL operations for reservations.
Connection details are read from environment variables:
  DB_HOSTNAME
Table is created automatically on first use.
"""

import logging
import os

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

DB_NAME = "sonicserve"

# ── Connection ────────────────────────────────────────────────────────────────

def _get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])

# ── Schema bootstrap ──────────────────────────────────────────────────────────

def ensure_table():
    """Create the reservations table if it does not exist yet."""
    ddl = """
    CREATE TABLE IF NOT EXISTS reservations (
        reservation_id  VARCHAR(16)  PRIMARY KEY,
        customer_name   TEXT         NOT NULL,
        party_size      INT          NOT NULL,
        datetime        VARCHAR(32)  NOT NULL,   -- stored as-is, e.g. "2025-03-13 18:30"
        phone           TEXT         NOT NULL,
        special_requests TEXT,
        status          VARCHAR(16)  NOT NULL DEFAULT 'CONFIRMED',
        created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    );
    """
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
            conn.commit()
        logger.info("[rds] reservations table ready")
    except Exception:
        logger.exception("[rds] Failed to ensure reservations table")


# ── Write ─────────────────────────────────────────────────────────────────────

def insert_reservation(
    reservation_id: str,
    customer_name: str,
    party_size: int,
    datetime_str: str,       # "YYYY-MM-DD HH:MM"
    phone: str,
    special_requests: str = "",
    status: str = "CONFIRMED",
) -> bool:
    """
    Insert a new reservation row.
    Returns True on success, False on failure (logs the error).
    """
    sql = """
    INSERT INTO reservations
        (reservation_id, customer_name, party_size, datetime, phone, special_requests, status)
    VALUES
        (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (reservation_id) DO NOTHING;
    """
    try:
        ensure_table()
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    reservation_id,
                    customer_name,
                    party_size,
                    datetime_str,
                    phone,
                    special_requests or "",
                    status,
                ))
            conn.commit()
        logger.info("[rds] Inserted reservation %s", reservation_id)
        return True
    except Exception:
        logger.exception("[rds] Failed to insert reservation %s", reservation_id)
        return False


def lookup_reservation(reservation_id: str) -> dict | None:
    """
    Look up a reservation by ID, normalising to uppercase first.
    Returns the row as a dict, or None if not found.
    """
    return get_reservation(reservation_id.upper())


def update_reservation_status(reservation_id: str, status: str) -> bool:
    """
    Update the status column for an existing reservation (e.g. 'CANCELLED').
    Normalises reservation_id to uppercase and verifies the row exists before
    writing; returns False (without raising) if the ID is not found.
    Returns True on success, False on failure.
    """
    normalised_id = reservation_id.upper()

    existing = lookup_reservation(normalised_id)
    if existing is None:
        logger.warning(
            "[rds] update_reservation_status: reservation %s not found — aborting.",
            normalised_id,
        )
        return False

    sql = "UPDATE reservations SET status = %s WHERE reservation_id = %s;"
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (status, normalised_id))
            conn.commit()
        logger.info("[rds] Updated reservation %s → %s", normalised_id, status)
        return True
    except Exception:
        logger.exception("[rds] Failed to update reservation %s", normalised_id)
        return False


# ── Read ──────────────────────────────────────────────────────────────────────

def get_reservation(reservation_id: str) -> dict | None:
    """
    Fetch a single reservation by ID.
    Returns a dict or None if not found.
    """
    sql = "SELECT * FROM reservations WHERE reservation_id = %s;"
    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (reservation_id,))
                row = cur.fetchone()
        return dict(row) if row else None
    except Exception:
        logger.exception("[rds] Failed to fetch reservation %s", reservation_id)
        return None