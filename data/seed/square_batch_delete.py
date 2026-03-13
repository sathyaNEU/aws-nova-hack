import os
from pathlib import Path
from dotenv import load_dotenv
from square import Square
from square.environment import SquareEnvironment

load_dotenv(Path(__file__).parent.parent.parent / ".env")

client = Square(
    token=os.environ["SQUARE_ACCESS_TOKEN"],
    environment=SquareEnvironment.SANDBOX
)

def delete_all_catalog_objects(types=("ITEM", "CATEGORY")):
    """
    Fetches all catalog objects of the given types and deletes them in bulk.
    Square's batch_delete accepts up to 200 IDs per call, so we chunk as needed.
    """
    object_ids = []

    # ── 1. Page through the entire catalog ────────────────────────────────
    # client.catalog.list() returns a SyncPager — iterate it directly.
    pager = client.catalog.list(types=",".join(types))

    for obj in pager:
        object_ids.append(obj.id)

    if not object_ids:
        print("No catalog objects found — nothing to delete.")
        return

    print(f"Found {len(object_ids)} object(s) to delete.")

    # ── 2. Batch-delete in chunks of 200 (Square's max per request) ────────
    chunk_size = 200
    deleted_total = 0

    for i in range(0, len(object_ids), chunk_size):
        chunk = object_ids[i : i + chunk_size]
        result = client.catalog.batch_delete(object_ids=chunk)

        if result.errors:
            raise Exception(f"Error deleting batch: {result.errors}")

        deleted = result.deleted_object_ids or []
        deleted_total += len(deleted)
        print(f"Deleted batch {i // chunk_size + 1}: {len(deleted)} object(s)")

    print(f"\n✅ Done. {deleted_total} object(s) deleted.")


if __name__ == "__main__":
    delete_all_catalog_objects()