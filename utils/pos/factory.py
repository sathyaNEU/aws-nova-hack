from utils.pos.base import POSProvider


def get_pos_provider(restaurant_name: str | None = None) -> POSProvider:
    """
    Return the appropriate POS provider for a given restaurant.

    TODO: look up pos_type from DB by restaurant_name / restaurant_id.
          For now, Square is hardcoded for all restaurants.
    """
    pos_type = "square"   # ← replace with DB lookup later

    if pos_type == "square":
        from utils.pos.square import SquarePOS
        return SquarePOS()

    if pos_type == "clover":
        from utils.pos.clover import CloverPOS
        return CloverPOS()

    raise ValueError(f"Unknown POS provider type: '{pos_type}'")