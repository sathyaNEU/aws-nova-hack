"""
data/master_data.py

In-memory store for all DB/API-backed data.
No SQL or HTTP here — delegates entirely to the rds/pos utility modules.
"""

import logging

from utils.rds.business_hours.core import fetch_all_business_hours
from utils.rds.policies.core import fetch_all_policies
from utils.pos.factory import get_pos_provider

logger = logging.getLogger(__name__)

master_data: dict = {
    "policies":       {},
    "business_hours": {},
    "menu":           {"categories": []},
}


def load():
    """
    Pull all remote data and populate master_data.
    Called once at startup inside mcp_server.py.
    """
    logger.info("[master_data] Loading policies…")
    master_data["policies"] = fetch_all_policies()
    logger.info("[master_data] Loaded %d policies", len(master_data["policies"]))

    logger.info("[master_data] Loading business_hours…")
    master_data["business_hours"] = fetch_all_business_hours()
    logger.info("[master_data] Loaded hours for %d days", len(master_data["business_hours"]))

    logger.info("[master_data] Loading menu from Square…")
    master_data["menu"] = get_pos_provider().fetch_menu()
    total = sum(len(c["items"]) for c in master_data["menu"]["categories"])
    logger.info("[master_data] Loaded %d menu items", total)


def reload():
    """Hot-reload without restarting."""
    load()
    logger.info("[master_data] Reloaded successfully")