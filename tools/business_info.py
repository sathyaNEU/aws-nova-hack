# ══════════════════════════════════════════════════════════════════════════════
# tools/business_info.py
# business hours now come from master_data["business_hours"] (loaded from DB).
# Location / parking still use the local RESTAURANT_INFO / PARKING_INFO dicts.
# ══════════════════════════════════════════════════════════════════════════════

from mcp.server.fastmcp import FastMCP
from data.master_data import master_data
from data.restaurant import RESTAURANT_INFO, PARKING_INFO

def register(mcp: FastMCP):

    @mcp.tool()
    def get_business_hours(day: str = "") -> dict:
        """
        Return the restaurant's opening hours.
        Optionally pass a day (e.g. 'monday') to get hours for a specific day.
        Returns all days if day is omitted or empty.
        """
        hours = master_data.get("business_hours", {})

        if day:
            day = day.strip().lower()
            if day in hours:
                return {"day": day, **hours[day]}
            return {"error": f"Unknown day '{day}'. Use a full weekday name, e.g. 'monday'."}

        return {
            "restaurant": RESTAURANT_INFO["name"],
            "timezone":   RESTAURANT_INFO["timezone"],
            "hours":      hours,
        }

    @mcp.tool()
    def get_location() -> dict:
        """Return the restaurant's address and contact phone number."""
        return {
            "name":    RESTAURANT_INFO["name"],
            "address": RESTAURANT_INFO["address"],
            "phone":   RESTAURANT_INFO["phone"],
        }

    @mcp.tool()
    def get_parking_info() -> dict:
        """
        Return all parking options near the restaurant:
        street parking, nearby garages, valet, and accessible spaces.
        """
        return PARKING_INFO