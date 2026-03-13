# tools/orders.py

import uuid
from datetime import datetime, timedelta

from mcp.server.fastmcp import FastMCP
from data.master_data import master_data
from utils.pos.factory import get_pos_provider


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_item_index() -> dict:
    """Build an item-id → item dict from the live master_data menu."""
    index = {}
    for cat in master_data["menu"]["categories"]:
        for item in cat["items"]:
            index[item["id"]] = item
    return index


def _resolve_items(line_items: list[dict]) -> tuple[list, list, float]:
    """
    Validate and price each line item against the Square catalog in master_data.
    Returns (resolved_lines, errors, subtotal).
    """
    item_index = _build_item_index()
    resolved, errors = [], []
    subtotal = 0.0

    for entry in line_items:
        item_id  = str(entry.get("item_id", "")).strip()
        quantity = int(entry.get("quantity", 1))
        notes    = entry.get("notes", "")

        if item_id not in item_index:
            errors.append(f"Unknown item_id '{item_id}'. Use get_menu to find valid IDs.")
            continue
        if quantity < 1:
            errors.append(f"Quantity for '{item_id}' must be at least 1.")
            continue

        item       = item_index[item_id]
        line_total = round(item["price"] * quantity, 2)
        subtotal  += line_total
        resolved.append({
            "item_id":      item_id,                           # Square item ID (lookup key)
            "variation_id": item.get("variation_id", item_id), # Square variation ID (sent to Orders API)
            "name":         item["name"],
            "unit_price":   item["price"],
            "quantity":     quantity,
            "line_total":   line_total,
            "notes":        notes or None,
        })

    return resolved, errors, round(subtotal, 2)


# ── Tool registration ─────────────────────────────────────────────────────────

def register(mcp: FastMCP):

    @mcp.tool()
    def place_order(
        customer_name: str,
        phone: str,
        order_type: str,
        line_items: list,
        pickup_time: str = "",
        special_instructions: str = "",
    ) -> dict:
        """
        Place a takeout or pickup order.

        Parameters
        ----------
        customer_name         : Full name of the customer.
        phone                 : Contact phone number.
        order_type            : 'takeout' or 'pickup' (synonymous here).
        line_items            : List of objects, each with:
                                  item_id  (str)  – Square item ID from get_menu
                                  quantity (int)  – number of units
                                  notes    (str)  – optional modifications
        pickup_time           : Requested pickup time in HH:MM (24h), e.g. '18:45'.
                                Leave blank for next available slot (~25 min).
        special_instructions  : Allergy notes or general instructions.

        Returns a full order confirmation JSON including the POS-side order ID.
        """
        order_type = order_type.strip().lower()
        if order_type not in ("takeout", "pickup"):
            return {"success": False, "error": "order_type must be 'takeout' or 'pickup'."}

        if pickup_time:
            try:
                datetime.strptime(pickup_time, "%H:%M")
            except ValueError:
                return {"success": False, "error": "Invalid pickup_time format. Use HH:MM (24h)."}

        if not line_items:
            return {"success": False, "error": "line_items cannot be empty."}

        resolved, errors, subtotal = _resolve_items(line_items)
        if errors:
            return {
                "success": False,
                "errors":  errors,
                "message": "Order could not be placed due to invalid items. Please correct and retry.",
            }

        TAX_RATE  = 0.08875
        tax       = round(subtotal * TAX_RATE, 2)
        total     = round(subtotal + tax, 2)
        est_ready = pickup_time or (datetime.now() + timedelta(minutes=25)).strftime("%H:%M")

        idempotency_key = uuid.uuid4().hex

        pos = get_pos_provider()
        pos_result = pos.create_order(
            customer_name=customer_name,
            phone=phone,
            order_type=order_type,
            line_items=resolved,
            estimated_ready_time=est_ready,
            special_instructions=special_instructions or None,
            idempotency_key=idempotency_key,
        )

        if not pos_result["success"]:
            return {
                "success": False,
                "error":   f"POS rejected the order: {pos_result['error']}",
                "pos_raw": pos_result.get("raw"),
            }

        confirmation = {
            "success":       True,
            "order_id":      idempotency_key,
            "pos_order_id":  pos_result["pos_order_id"],
            "pos_status":    pos_result["status"],
            "restaurant":    "Bella Tavola",
            "customer_name": customer_name,
            "phone":         phone,
            "order_type":    order_type,
            "status":        "RECEIVED",
            "line_items":    resolved,
            "special_instructions":  special_instructions or None,
            "estimated_ready_time":  est_ready,
            "pickup_address":        "142 Oak Street, Brooklyn, NY 11201",
            "created_at":            datetime.utcnow().isoformat() + "Z",
        }

        print("===============================")
        print(confirmation)
        print("===============================")
        return confirmation

    @mcp.tool()
    def get_order_status(order_id: str) -> dict:
        """
        Return the current status of a placed order.

        Parameters
        ----------
        order_id : The Square order ID returned in pos_order_id when the
                   order was placed.
        """
        pos = get_pos_provider()
        result = pos.get_order_status(order_id)

        if not result["success"]:
            return {"success": False, "error": result["error"]}

        return {
            "success":  True,
            "order_id": order_id,
            "status":   result["status"],
            "message":  "Your order is being prepared and will be ready for pickup shortly.",
        }