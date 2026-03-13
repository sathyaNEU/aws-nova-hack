"""
Clover Sandbox Menu Loader
Loads all categories + items into your Clover sandbox merchant.

Usage:
    pip install requests python-dotenv
    python clover_loader.py

data/.env file:
    CLOVER_MERCHANT_ID=your_merchant_id
    CLOVER_API_TOKEN=your_api_token
"""

import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# ─── Config ───────────────────────────────────────────────────────────────────

load_dotenv(Path(__file__).parent.parent.parent / ".env")

MERCHANT_ID = os.getenv("CLOVER_MERCHANT_ID")
API_TOKEN   = os.getenv("CLOVER_API_TOKEN")

if not MERCHANT_ID or not API_TOKEN:
    raise SystemExit("❌ Missing CLOVER_MERCHANT_ID or CLOVER_API_TOKEN in data/.env")

BASE_URL = f"https://apisandbox.dev.clover.com/v3/merchants/{MERCHANT_ID}"
HEADERS  = {
    "Content-Type":  "application/json",
    "Authorization": f"Bearer {API_TOKEN}",
}

# ─── Menu Data ────────────────────────────────────────────────────────────────

CATEGORIES = [
    {"key": "starters",   "name": "Starters"},
    {"key": "burgers",    "name": "Burgers"},
    {"key": "sandwiches", "name": "Sandwiches"},
    {"key": "mains",      "name": "Mains"},
    {"key": "desserts",   "name": "Desserts"},
    {"key": "drinks",     "name": "Drinks"},
]

ITEMS = [
    # Starters
    {"category": "starters",   "name": "Buffalo Wings",            "price": 1400, "description": "Crispy chicken wings tossed in classic buffalo sauce, served with ranch."},
    {"category": "starters",   "name": "Mozzarella Sticks",        "price": 1100, "description": "Breaded mozzarella sticks fried golden, served with marinara."},
    {"category": "starters",   "name": "Loaded Nachos",            "price": 1300, "description": "Tortilla chips topped with melted cheese, jalapeños, sour cream, and salsa."},
    # Burgers
    {"category": "burgers",    "name": "Classic Cheeseburger",     "price": 1500, "description": "Beef patty, cheddar cheese, lettuce, tomato, pickles, brioche bun."},
    {"category": "burgers",    "name": "BBQ Bacon Burger",         "price": 1700, "description": "Beef patty, crispy bacon, cheddar, onion rings, BBQ sauce."},
    {"category": "burgers",    "name": "Veggie Burger",            "price": 1400, "description": "Plant-based patty, lettuce, tomato, avocado, vegan aioli."},
    {"category": "burgers",    "name": "Mushroom Swiss Burger",    "price": 1600, "description": "Beef patty topped with sautéed mushrooms and Swiss cheese."},
    # Sandwiches
    {"category": "sandwiches", "name": "Grilled Chicken Sandwich", "price": 1400, "description": "Grilled chicken breast, lettuce, tomato, honey mustard."},
    {"category": "sandwiches", "name": "Philly Cheesesteak",       "price": 1600, "description": "Shaved beef, grilled onions, peppers, melted provolone."},
    {"category": "sandwiches", "name": "Pulled Pork Sandwich",     "price": 1500, "description": "Slow-smoked pulled pork, coleslaw, BBQ sauce on brioche bun."},
    # Mains
    {"category": "mains",      "name": "BBQ Ribs",                 "price": 2800, "description": "Slow-cooked pork ribs glazed with house BBQ sauce."},
    {"category": "mains",      "name": "Fried Chicken Plate",      "price": 2000, "description": "Southern-style fried chicken served with mashed potatoes and gravy."},
    {"category": "mains",      "name": "New York Strip Steak",     "price": 3400, "description": "Grilled 12 oz NY strip served with garlic butter and fries."},
    {"category": "mains",      "name": "Mac & Cheese",             "price": 1600, "description": "Creamy baked macaroni with cheddar cheese sauce."},
    # Desserts
    {"category": "desserts",   "name": "New York Cheesecake",      "price": 1000, "description": "Classic cheesecake with strawberry sauce."},
    {"category": "desserts",   "name": "Chocolate Brownie Sundae", "price": 1100, "description": "Warm chocolate brownie topped with vanilla ice cream."},
    {"category": "desserts",   "name": "Apple Pie",                "price":  900, "description": "Classic American apple pie served warm."},
    # Drinks
    {"category": "drinks",     "name": "Coca-Cola",                "price":  300},
    {"category": "drinks",     "name": "Iced Tea",                 "price":  300},
    {"category": "drinks",     "name": "Lemonade",                 "price":  400},
    {"category": "drinks",     "name": "Craft Beer (Pint)",        "price":  700},
    {"category": "drinks",     "name": "Espresso",                 "price":  400},
]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def post(path: str, body: dict) -> dict:
    res = requests.post(f"{BASE_URL}{path}", json=body, headers=HEADERS)
    if not res.ok:
        raise RuntimeError(f"POST {path} failed ({res.status_code}): {res.text}")
    return res.json()

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=== Clover Menu Loader ===\n")

    # Step 1: Create categories
    print("Step 1: Creating categories...")
    category_id_map = {}

    for cat in CATEGORIES:
        data = post("/categories", {"name": cat["name"]})
        category_id_map[cat["key"]] = data["id"]
        print(f"  ✓ {cat['name']} → {data['id']}")
        time.sleep(0.2)

    # Step 2: Create items
    print("\nStep 2: Creating items...")
    created_items = []

    for item in ITEMS:
        body = {
            "name":             item["name"],
            "price":            item["price"],
            "priceType":        "FIXED",
            "isRevenue":        True,
            "defaultTaxRates":  True,
        }
        if "description" in item:
            body["alternateName"] = item["description"]

        data = post("/items", body)
        created_items.append({
            **item,
            "clover_id":   data["id"],
            "category_id": category_id_map[item["category"]],
        })
        print(f"  ✓ {item['name']} → {data['id']}")
        time.sleep(0.2)

    # Step 3: Link items to categories
    print("\nStep 3: Linking items to categories...")

    for item in created_items:
        post("/category_items", {
            "elements": [
                {"item": {"id": item["clover_id"]}, "category": {"id": item["category_id"]}}
            ]
        })
        print(f"  ✓ \"{item['name']}\" → category \"{item['category']}\"")
        time.sleep(0.2)

    print("\n✅ Done! All categories and items loaded into Clover sandbox.")


if __name__ == "__main__":
    main()