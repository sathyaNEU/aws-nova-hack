import os
from datetime import datetime, timezone
import httpx
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("America/New_York")
from utils.pos.base import POSProvider

_CLOVER_BASE = {
    "sandbox":    "https://apisandbox.dev.clover.com",
    "production": "https://api.clover.com",
}


class CloverPOS(POSProvider):
    """
    Clover Orders API integration.

    Required env vars:
        CLOVER_API_TOKEN   – Bearer token (sandbox or production)
        CLOVER_MERCHANT_ID – Merchant ID from the Clover dashboard URL
        CLOVER_ENV         – 'sandbox' (default) or 'production'
    """

    def __init__(self):
        token = os.getenv("CLOVER_API_TOKEN")
        if not token:
            raise EnvironmentError("CLOVER_API_TOKEN is not set in the environment.")

        self.merchant_id = os.getenv("CLOVER_MERCHANT_ID")
        if not self.merchant_id:
            raise EnvironmentError("CLOVER_MERCHANT_ID is not set in the environment.")

        env = os.getenv("CLOVER_ENV", "sandbox").lower()
        base_url = _CLOVER_BASE.get(env, _CLOVER_BASE["sandbox"])

        self._base_url = f"{base_url}/v3/merchants/{self.merchant_id}"
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        }

    # ── helpers ────────────────────────────────────────────────────────────────

    def _build_line_items(self, line_items: list[dict]) -> list[dict]:
        """
        Convert internal line-item format to Clover LineItem objects.

        Each internal item has:
            item_id    : internal SKU (informational only)
            name       : display name
            unit_price : float (dollars)
            quantity   : int
            notes      : str | None
        """
        cl_items = []
        for li in line_items:
            cl_item: dict = {
                "name":     li["name"],
                "price":    int(round(li["unit_price"] * 100)),  # cents
                "unitQty":  li["quantity"],
            }
            if li.get("notes"):
                cl_item["note"] = li["notes"]
            cl_items.append(cl_item)
        return cl_items

    @staticmethod
    def _hhmm_to_unix_ms(hhmm: str) -> int:
        """
        Convert 'HH:MM' local restaurant time to Unix timestamp in milliseconds.
        Clover uses epoch milliseconds for pickup times.
        """
        now_local = datetime.now(LOCAL_TZ)
        hour, minute = map(int, hhmm.split(":"))
        local_dt = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        utc_dt = local_dt.astimezone(timezone.utc)
        return int(utc_dt.timestamp() * 1000)

    # ── POSProvider interface ──────────────────────────────────────────────────

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
        # Step 1: Create the order
        order_payload = {
            "orderType": {"id": order_type},   # maps to a pre-configured Clover order type ID
            "note":      special_instructions or "",
            "state":     "open",
            "manualTransaction": False,
        }

        try:
            resp = httpx.post(
                f"{self._base_url}/orders",
                headers=self._headers,
                json=order_payload,
                timeout=15.0,
            )
            data = resp.json()
        except httpx.RequestError as exc:
            return {"success": False, "error": f"HTTP request failed: {exc}", "raw": {}}

        if resp.status_code not in (200, 201) or "id" not in data:
            return {
                "success": False,
                "error":   data.get("message", resp.text),
                "raw":     data,
            }

        order_id = data["id"]

        # Step 2: Add line items to the order
        for li in self._build_line_items(line_items):
            try:
                li_resp = httpx.post(
                    f"{self._base_url}/orders/{order_id}/line_items",
                    headers=self._headers,
                    json=li,
                    timeout=15.0,
                )
                if li_resp.status_code not in (200, 201):
                    return {
                        "success": False,
                        "error":   f"Failed to add line item '{li['name']}': {li_resp.text}",
                        "raw":     li_resp.json(),
                    }
            except httpx.RequestError as exc:
                return {"success": False, "error": f"HTTP request failed: {exc}", "raw": {}}

        # Step 3: Attach customer info as order note (Clover has no native pickup block)
        customer_note = f"Customer: {customer_name} | Phone: {phone}"
        if estimated_ready_time:
            customer_note += f" | Pickup: {estimated_ready_time}"

        try:
            httpx.post(
                f"{self._base_url}/orders/{order_id}",
                headers=self._headers,
                json={"note": customer_note},
                timeout=15.0,
            )
        except httpx.RequestError:
            pass  # non-fatal — order is already created

        return {
            "success":      True,
            "pos_order_id": order_id,
            "status":       data.get("state", "open"),
            "raw":          data,
        }

    def get_order_status(self, pos_order_id: str) -> dict:
        try:
            resp = httpx.get(
                f"{self._base_url}/orders/{pos_order_id}",
                headers=self._headers,
                timeout=15.0,
            )
            data = resp.json()
        except httpx.RequestError as exc:
            return {"success": False, "error": str(exc), "raw": {}}

        if resp.status_code != 200 or "id" not in data:
            return {
                "success": False,
                "error":   data.get("message", resp.text),
                "raw":     data,
            }

        return {
            "success": True,
            "status":  data.get("state", "UNKNOWN"),
            "raw":     data,
        }