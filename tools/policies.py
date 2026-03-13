# ══════════════════════════════════════════════════════════════════════════════
# tools/policies.py
# Reads from master_data["policies"] (loaded from DB at startup).
# ══════════════════════════════════════════════════════════════════════════════

from mcp.server.fastmcp import FastMCP
from data.master_data import master_data

_VALID_TOPICS = [
    "reservations", "takeout_pickup", "dress_code", "children",
    "outside_beverages", "corkage_fee", "pets", "accessibility",
    "payment_methods", "gratuity", "gift_cards", "private_events",
]

def register(mcp: FastMCP):

    @mcp.tool()
    def get_policy(topic: str = "") -> dict:
        """
        Return restaurant policy information.
        Pass a specific topic to get focused info, or omit to receive all policies.

        Valid topics: reservations, takeout_pickup, dress_code, children,
        outside_beverages, corkage_fee, pets, accessibility, payment_methods,
        gratuity, gift_cards, private_events.
        """
        policies = master_data.get("policies", {})

        if not topic:
            return policies

        topic = topic.strip().lower()
        if topic in policies:
            return {topic: policies[topic]}

        return {
            "error": f"Unknown topic '{topic}'.",
            "valid_topics": _VALID_TOPICS,
        }
