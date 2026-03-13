from abc import ABC, abstractmethod


class POSProvider(ABC):
    """
    Abstract interface every POS integration must implement.
    orders.py calls only these methods — provider details stay internal.
    """

    @abstractmethod
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
        """
        Submit an order to the POS system.

        Must return a dict with at minimum:
            success      : bool
            pos_order_id : str   (POS-side order ID)
            raw          : dict  (full POS response, for debugging)

        On failure:
            success      : bool = False
            error        : str
            raw          : dict
        """
        ...

    @abstractmethod
    def get_order_status(self, pos_order_id: str) -> dict:
        """
        Retrieve current status of an order from the POS system.

        Must return:
            success : bool
            status  : str
            raw     : dict
        """
        ...