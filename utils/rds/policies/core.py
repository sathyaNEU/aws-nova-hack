"""
utils/rds/policies/core.py

PostgreSQL operations for the policy_information table.

Schema:
  policy_information
    policy_name  VARCHAR  PRIMARY KEY
    description  TEXT     NOT NULL
"""

import logging
import os

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


# ── Connection ────────────────────────────────────────────────────────────────

def _get_conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


# ── Read ──────────────────────────────────────────────────────────────────────

def fetch_all_policies() -> dict:
    """
    Fetch all rows from policy_information and return a dict keyed by policy_name.

    Example return value:
      {
        "reservations":  "Reservations can be booked ...",
        "dress_code":    "Smart casual. No athletic wear ...",
        ...
      }
    """
    sql = "SELECT policy_name, description FROM policy_information ORDER BY policy_name;"
    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchall()
        result = {r["policy_name"]: r["description"] for r in rows}
        logger.info("[rds] Fetched %d policies", len(result))
        return result
    except Exception:
        logger.exception("[rds] Failed to fetch policies")
        return {}