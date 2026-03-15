#utils/pos/square.py
import os
from datetime import datetime, timezone
import httpx
from zoneinfo import ZoneInfo
from utils.pos.base import POSProvider
import logging
import uuid

logger = logging.getLogger(__name__)
LOCAL_TZ = ZoneInfo("America/New_York")

_SQUARE_BASE = {
    "sandbox":    "https://connect.squareupsandbox.com",
    "production": "https://connect.squareup.com",
}

SQUARE_VERSION = "2025-09-24"


class SquarePOS(POSProvider):
    """
    Square Orders API + Catalog API integration.

    Required env vars:
        SQUARE_ACCESS_TOKEN  – Bearer token (sandbox or production)
        SQUARE_LOCATION_ID   – Location ID orders are created under
        SQUARE_ENV           – 'sandbox' (default) or 'production'
    """

    def __init__(self):
        token = os.getenv("SQUARE_ACCESS_TOKEN")
        if not token:
            raise EnvironmentError("SQUARE_ACCESS_TOKEN is not set in the environment.")

        self.location_id = os.getenv("SQUARE_LOCATION_ID")
        if not self.location_id:
            raise EnvironmentError("SQUARE_LOCATION_ID is not set in the environment.")

        env = os.getenv("SQUARE_ENV", "sandbox").lower()
        self._base_url = _SQUARE_BASE.get(env, _SQUARE_BASE["sandbox"])
        self._headers = {
            "Authorization":  f"Bearer {token}",
            "Content-Type":   "application/json",
            "Square-Version": SQUARE_VERSION,
        }

    def _generate_order_code(self) -> str:
        """Generate a 6-character uppercase order code from UUID."""
        return uuid.uuid4().hex[:6].upper()

    # ── Catalog ───────────────────────────────────────────────────────────────

    def _list_catalog_objects(self) -> list:
        """Paginate through /v2/catalog/list for ITEM, ITEM_VARIATION, CATEGORY."""
        objects, cursor = [], None

        while True:
            params = {"types": "ITEM,ITEM_VARIATION,CATEGORY"}
            if cursor:
                params["cursor"] = cursor

            resp = httpx.get(
                f"{self._base_url}/v2/catalog/list",
                headers=self._headers,
                params=params,
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("errors"):
                raise RuntimeError(f"Square catalog errors: {data['errors']}")

            objects.extend(data.get("objects", []))
            cursor = data.get("cursor")
            if not cursor:
                break

        return objects

    def fetch_menu(self) -> dict:
        try:
            objects = self._list_catalog_objects()
        except Exception:
            logger.exception("[square] Failed to fetch catalog")
            return {"categories": []}

        categories: dict[str, str] = {}
        buckets:    dict[str, list] = {}

        for obj in objects:
            if obj.get("type") == "CATEGORY":
                categories[obj["id"]] = obj.get("category_data", {}).get("name", "Other")

        items = [o for o in objects if o.get("type") == "ITEM"]

        for obj in items:
            item_data    = obj.get("item_data", {})
            cats         = item_data.get("categories", [])
            category_id  = cats[0]["id"] if cats else ""
            category_name = categories.get(category_id, "Other")

            variations  = item_data.get("variations", [])
            price_cents = 0
            variation_id = obj["id"]  # fallback
            if variations:
                price_cents  = (
                    variations[0]
                    .get("item_variation_data", {})
                    .get("price_money", {})
                    .get("amount", 0)
                )
                variation_id = variations[0]["id"]  # ← store the variation ID

            buckets.setdefault(category_name, []).append({
                "id":           obj["id"],
                "variation_id": variation_id,  # ← added
                "name":         item_data.get("name", ""),
                "price":        round(price_cents / 100, 2),
                "description":  item_data.get("description", ""),
            })

        menu = {
            "categories": [
                {"name": cat_name, "items": cat_items}
                for cat_name, cat_items in sorted(buckets.items())
            ]
        }

        total = sum(len(c["items"]) for c in menu["categories"])
        logger.info("[square] Loaded %d items across %d categories", total, len(menu["categories"]))
        return menu

    def _build_line_items(self, line_items: list[dict]) -> list[dict]:
        sq_items = []
        for li in line_items:
            sq_item: dict = {
                "name":              li["name"],
                "quantity":          str(li["quantity"]),
                "catalog_object_id": li["variation_id"],  # ← was li["item_id"]
            }
            if li.get("notes"):
                sq_item["note"] = li["notes"]
            sq_items.append(sq_item)
        return sq_items

    @staticmethod
    def _hhmm_to_rfc3339(hhmm: str) -> str:
        """Convert 'HH:MM' local restaurant time to RFC3339 UTC timestamp."""
        now_local = datetime.now(LOCAL_TZ)
        hour, minute = map(int, hhmm.split(":"))
        local_dt = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return local_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _build_fulfillment(
        self,
        customer_name: str,
        phone: str,
        estimated_ready_time: str,
        special_instructions: str | None,
    ) -> dict:
        pickup_detail: dict = {
            "recipient": {
                "display_name": customer_name,
                "phone_number": phone,
            },
            "pickup_at":     self._hhmm_to_rfc3339(estimated_ready_time),
            "schedule_type": "SCHEDULED" if estimated_ready_time else "ASAP",
        }
        if special_instructions:
            pickup_detail["note"] = special_instructions
        return {
            "type":           "PICKUP",
            "state":          "PROPOSED",
            "pickup_details": pickup_detail,
        }

    def complete_payment(self, *, pos_order_id: str, amount_cents: int) -> dict:
        """
        Sandbox only: attach a payment to an order using the test card nonce
        so the order appears as OPEN/paid in the Square POS dashboard.
        """
        try:
            resp = httpx.post(
                f"{self._base_url}/v2/payments",
                headers=self._headers,
                json={
                    "idempotency_key": str(uuid.uuid4()),
                    "source_id":       "cnon:card-nonce-ok",
                    "amount_money":    {"amount": amount_cents, "currency": "USD"},
                    "order_id":        pos_order_id,
                    "location_id":     self.location_id,
                },
                timeout=15.0,
            )
            data = resp.json()
        except httpx.RequestError as exc:
            return {"success": False, "error": f"HTTP request failed: {exc}"}

        if resp.status_code not in (200, 201) or "errors" in data:
            errors = data.get("errors", [{"detail": resp.text}])
            return {"success": False, "error": "; ".join(e.get("detail", "") for e in errors)}

        return {
            "success":    True,
            "payment_id": data["payment"]["id"],
            "status":     data["payment"].get("status"),
        }

    def create_order(
        self,
        *,
        customer_name: str,
        phone: str,
        order_type: str,
        line_items: list[dict],
        estimated_ready_time: str,
        special_instructions: str | None,
        idempotency_key: str,
    ) -> dict:
        order_code = self._generate_order_code()
        payload = {
            "idempotency_key": idempotency_key,
            "order": {
                "location_id":  self.location_id,
                "reference_id": order_code,
                "line_items":   self._build_line_items(line_items),
                "fulfillments": [
                    self._build_fulfillment(
                        customer_name,
                        phone,
                        estimated_ready_time,
                        special_instructions,
                    )
                ],
                "metadata": {
                    "source":         "voice_agent",
                    "order_type":     order_type,
                    "customer_phone": phone,
                },
            },
        }

        try:
            resp = httpx.post(
                f"{self._base_url}/v2/orders",
                headers=self._headers,
                json=payload,
                timeout=15.0,
            )
            data = resp.json()
        except httpx.RequestError as exc:
            return {"success": False, "error": f"HTTP request failed: {exc}", "raw": {}}

        if resp.status_code not in (200, 201) or "errors" in data:
            errors = data.get("errors", [{"detail": resp.text}])
            return {
                "success": False,
                "error":   "; ".join(e.get("detail", "Unknown error") for e in errors),
                "raw":     data,
            }

        sq_order     = data["order"]
        pos_order_id = sq_order["id"]

        # ── Sandbox: auto-complete payment so order is visible in POS ─────────
        if os.getenv("SQUARE_ENV", "sandbox").lower() == "sandbox":
            total_cents = sq_order.get("total_money", {}).get("amount", 0)
            pay_result  = self.complete_payment(
                pos_order_id=pos_order_id,
                amount_cents=total_cents,
            )
            if not pay_result["success"]:
                logger.warning("[square] Payment completion failed: %s", pay_result["error"])

        return {
            "success":      True,
            "pos_order_id": pos_order_id,
            "order_code":   order_code,
            "status":       sq_order.get("state", "OPEN"),
            "raw":          data,
        }

    def get_order_status(self, pos_order_id: str) -> dict:
        try:
            resp = httpx.get(
                f"{self._base_url}/v2/orders/{pos_order_id}",
                headers=self._headers,
                timeout=15.0,
            )
            data = resp.json()
        except httpx.RequestError as exc:
            return {"success": False, "error": str(exc), "raw": {}}

        if resp.status_code != 200 or "errors" in data:
            errors = data.get("errors", [{"detail": resp.text}])
            return {
                "success": False,
                "error":   "; ".join(e.get("detail", "") for e in errors),
                "raw":     data,
            }

        sq_order = data["order"]
        return {
            "success": True,
            "status":  sq_order.get("state", "UNKNOWN"),
            "raw":     data,
        }
