# tools/menu.py

from mcp.server.fastmcp import FastMCP
from data.master_data import master_data


# ── Helpers ───────────────────────────────────────────────────────────────────

def _all_items():
    for cat in master_data["menu"]["categories"]:
        for item in cat["items"]:
            yield {**item, "category": cat["name"]}


# ── Tool registration ─────────────────────────────────────────────────────────

def register(mcp: FastMCP):

    @mcp.tool()
    def get_menu(category: str = "") -> dict:
        """
        Return the full menu, or just one category if specified.
        Pass category name e.g. 'Burgers', 'Drinks'. Omit for the full menu.
        When a caller asks a general question about the menu or what's available,
        always call this with no argument so the full menu is in context.
        """
        menu = master_data["menu"]

        if not category:
            return menu

        category = category.strip().lower()
        for cat in menu["categories"]:
            if cat["name"].lower() == category:
                return {"category": cat["name"], "items": cat["items"]}

        available = [c["name"] for c in menu["categories"]]
        return {"error": f"Category '{category}' not found.", "available_categories": available}

    @mcp.tool()
    def search_menu(
        max_price: float = 0.0,
        keyword: str = "",
    ) -> dict:
        """
        Search the menu by price ceiling or a keyword in the item name or description.
        Dietary info and allergens are embedded in each item's description.

        max_price : maximum price in USD (0 = no limit)
        keyword   : free-text search across name and description
        """
        results = list(_all_items())

        if max_price and max_price > 0:
            results = [i for i in results if i.get("price", 0) <= max_price]

        if keyword:
            kw = keyword.strip().lower()
            results = [
                i for i in results
                if kw in i["name"].lower() or kw in i.get("description", "").lower()
            ]

        if not results:
            return {"message": "No items matched the given filters.", "items": []}
        return {"count": len(results), "items": results}