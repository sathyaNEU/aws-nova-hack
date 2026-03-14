"""
Tool: mark_item_sold_out
Finds an item variation in Square by SKU/name and marks it as sold out
on both Point of Sale and Online (sets location_overrides.sold_out = True).

Uses squareup_legacy (v41) — the stable SDK. The new v42 SDK has breaking
changes that make catalog upsert unreliable.
"""
import os
import uuid

from square_legacy.client import Client
from strands import tool


def _get_client() -> Client:
    env = os.getenv("SQUARE_ENV", "sandbox")
    print(f"[square] Creating Square client (env={env})")
    client = Client(
        access_token=os.environ["SQUARE_ACCESS_TOKEN"],
        environment="sandbox" if env == "sandbox" else "production",
    )
    print("[square] Square client ready")
    return client


def _find_variation(client: Client, sku_or_name: str):
    print(f"[square] Searching catalog for: {sku_or_name!r}")

    # Try variation search first (reliable for SKUs)
    result = client.catalog.search_catalog_objects(body={
        "object_types": ["ITEM_VARIATION"],
        "query": {"text_query": {"keywords": [sku_or_name]}},
        "include_related_objects": True,
    })
    if result.is_error():
        raise RuntimeError(f"Square catalog search failed: {result.errors}")

    objects = result.body.get("objects") or []

    # Fallback: search by parent item name using prefix_query
    if not objects:
        print(f"[square] No variation match — trying prefix_query on item name")
        result = client.catalog.search_catalog_objects(body={
            "object_types": ["ITEM"],
            "query": {
                "prefix_query": {
                    "attribute_name": "name",
                    "attribute_prefix": sku_or_name,
                }
            },
            "include_related_objects": True,
        })
        if result.is_error():
            raise RuntimeError(f"Square catalog search failed: {result.errors}")

        objects = result.body.get("objects") or []
        print(f"[square] prefix_query returned {len(objects)} item(s)")

        if not objects:
            raise ValueError(
                f"No catalog item or variation found matching '{sku_or_name}'. "
                "Make sure the name matches what's in Square."
            )

        # Grab the first variation from the matched parent item
        parent = objects[0]
        variations = parent.get("item_data", {}).get("variations") or []
        if not variations:
            raise ValueError(f"Item '{sku_or_name}' has no variations.")

        variation = variations[0]
        print(f"[square] Using variation id={variation['id']} from parent item")
        return parent, variation

    # Original path (SKU match)
    variation = objects[0]
    print(f"[square] Using variation id={variation['id']}")
    related = {o["id"]: o for o in result.body.get("related_objects") or []}
    parent_id = variation.get("item_variation_data", {}).get("item_id")
    parent = related.get(parent_id)
    return parent, variation

def _set_sold_out_status(client: Client, variation: dict, location_id: str, sold_out: bool):
    """Shared helper — sets or clears sold_out + track_inventory on a variation."""
    var_data = variation.get("item_variation_data", {})
    overrides = list(var_data.get("location_overrides") or [])
    print(f"[square] Existing location_overrides: {overrides}")

    updated = False
    for o in overrides:
        if o.get("location_id") == location_id:
            o["sold_out"] = sold_out
            o["track_inventory"] = sold_out   # disable tracking when back in stock
            updated = True
            break
    if not updated:
        overrides.append({
            "location_id": location_id,
            "sold_out": sold_out,
            "track_inventory": sold_out,
        })

    print(f"[square] Setting sold_out={sold_out}, track_inventory={sold_out}")

    result = client.catalog.upsert_catalog_object(body={
        "idempotency_key": str(uuid.uuid4()),
        "object": {
            "type": "ITEM_VARIATION",
            "id": variation["id"],
            "version": variation.get("version"),
            "item_variation_data": {
                **var_data,
                "track_inventory": sold_out,  # global default mirrors location setting
                "location_overrides": overrides,
            },
        },
    })

    if result.is_error():
        raise RuntimeError(f"Square upsert failed: {result.errors}")

    print(f"[square] Upsert successful")


@tool
def mark_item_sold_out(item_identifier: str) -> str:
    """
    Mark a Square catalog item variation as sold out on Point of Sale and Online.

    Use this when the user says things like:
      - "item-s01 ran out"
      - "we're out of the BBQ Bacon Burger"
      - "mark SKU ITEM-S01 as sold out"

    Args:
        item_identifier: The SKU, item name, or partial name of the item.

    Returns:
        A confirmation message with the item name and variation updated.
    """
    print(f"[square] mark_item_sold_out called — item_identifier={item_identifier!r}")
    location_id = os.environ["SQUARE_LOCATION_ID"]
    client = _get_client()
    parent, variation = _find_variation(client, item_identifier)
    _set_sold_out_status(client, variation, location_id, sold_out=True)

    var_data = variation.get("item_variation_data", {})
    var_name = var_data.get("name", "Unknown variation")
    item_name = (parent or {}).get("item_data", {}).get("name", "Unknown item")

    result = (
        f"✅ Marked *{item_name} – {var_name}* as *sold out* 🔴 "
        f"on Point of Sale and Online."
    )
    print(f"[square] Done — {result}")
    return result


@tool
def mark_item_back_in_stock(item_identifier: str) -> str:
    """
    Mark a Square catalog item variation as available again (undo sold out).
    Disables inventory tracking and clears the sold_out flag so the item
    appears normally on Point of Sale and Online.

    Use this when the user says things like:
      - "BBQ Bacon Burger is back"
      - "we have SKU2 again"
      - "item-s01 is restocked"
      - "mark BBQ Bacon Burger as available"

    Args:
        item_identifier: The SKU, item name, or partial name of the item.

    Returns:
        A confirmation message confirming the item is available again.
    """
    print(f"[square] mark_item_back_in_stock called — item_identifier={item_identifier!r}")
    location_id = os.environ["SQUARE_LOCATION_ID"]
    client = _get_client()
    parent, variation = _find_variation(client, item_identifier)
    _set_sold_out_status(client, variation, location_id, sold_out=False)

    var_data = variation.get("item_variation_data", {})
    var_name = var_data.get("name", "Unknown variation")
    item_name = (parent or {}).get("item_data", {}).get("name", "Unknown item")

    result = (
        f"✅ Marked *{item_name} – {var_name}* as *available* 🟢 "
        f"on Point of Sale and Online."
    )
    print(f"[square] Done — {result}")
    return result