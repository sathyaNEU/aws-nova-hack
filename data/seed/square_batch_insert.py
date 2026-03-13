import os
from pathlib import Path
from dotenv import load_dotenv
from square import Square
from square.environment import SquareEnvironment

load_dotenv(Path(__file__).parent.parent.parent / ".env")

client = Square(
    token=os.environ["SQUARE_ACCESS_TOKEN"],
    environment=SquareEnvironment.SANDBOX  # change to SquareEnvironment.PRODUCTION when ready
)

client.catalog.batch_upsert(
    idempotency_key="menu-import-v5",
    batches=[
        {
            "objects": [

                # ── Categories ────────────────────────────────────────────
                {
                    "type": "CATEGORY", "id": "#cat-starters",
                    "present_at_all_locations": True,
                    "category_data": {"name": "Starters"}
                },
                {
                    "type": "CATEGORY", "id": "#cat-burgers",
                    "present_at_all_locations": True,
                    "category_data": {"name": "Burgers"}
                },
                {
                    "type": "CATEGORY", "id": "#cat-sandwiches",
                    "present_at_all_locations": True,
                    "category_data": {"name": "Sandwiches"}
                },
                {
                    "type": "CATEGORY", "id": "#cat-mains",
                    "present_at_all_locations": True,
                    "category_data": {"name": "Mains"}
                },
                {
                    "type": "CATEGORY", "id": "#cat-desserts",
                    "present_at_all_locations": True,
                    "category_data": {"name": "Desserts"}
                },
                {
                    "type": "CATEGORY", "id": "#cat-drinks",
                    "present_at_all_locations": True,
                    "category_data": {"name": "Drinks"}
                },

                # ── Starters ──────────────────────────────────────────────
                {
                    "type": "ITEM", "id": "#item-S01",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Buffalo Wings",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Crispy chicken wings tossed in classic buffalo sauce, served with ranch. Gluten-Free | Halal",
                        "categories": [{"id": "#cat-starters"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-S01",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-S01", "name": "Regular",
                                "sku": "SKU001",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 1400, "currency": "USD"}
                            }
                        }]
                    }
                },
                {
                    "type": "ITEM", "id": "#item-S02",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Mozzarella Sticks",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Breaded mozzarella sticks fried golden, served with marinara. Vegetarian | Contains Dairy | Contains Gluten",
                        "categories": [{"id": "#cat-starters"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-S02",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-S02", "name": "Regular",
                                "sku": "SKU002",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 1100, "currency": "USD"}
                            }
                        }]
                    }
                },
                {
                    "type": "ITEM", "id": "#item-S03",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Loaded Nachos",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Tortilla chips topped with melted cheese, jalapeños, sour cream, and salsa. Vegetarian | Gluten-Free | Contains Dairy",
                        "categories": [{"id": "#cat-starters"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-S03",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-S03", "name": "Regular",
                                "sku": "SKU003",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 1300, "currency": "USD"}
                            }
                        }]
                    }
                },

                # ── Burgers ───────────────────────────────────────────────
                {
                    "type": "ITEM", "id": "#item-B01",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Classic Cheeseburger",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Beef patty, cheddar cheese, lettuce, tomato, pickles, brioche bun. Contains Dairy | Contains Gluten",
                        "categories": [{"id": "#cat-burgers"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-B01",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-B01", "name": "Regular",
                                "sku": "SKU004",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 1500, "currency": "USD"}
                            }
                        }]
                    }
                },
                {
                    "type": "ITEM", "id": "#item-B02",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "BBQ Bacon Burger",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Beef patty, crispy bacon, cheddar, onion rings, BBQ sauce. Contains Dairy | Contains Gluten",
                        "categories": [{"id": "#cat-burgers"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-B02",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-B02", "name": "Regular",
                                "sku": "SKU005",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 1700, "currency": "USD"}
                            }
                        }]
                    }
                },
                {
                    "type": "ITEM", "id": "#item-B03",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Veggie Burger",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Plant-based patty, lettuce, tomato, avocado, vegan aioli. Vegan | Dairy-Free | Contains Gluten",
                        "categories": [{"id": "#cat-burgers"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-B03",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-B03", "name": "Regular",
                                "sku": "SKU006",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 1400, "currency": "USD"}
                            }
                        }]
                    }
                },
                {
                    "type": "ITEM", "id": "#item-B04",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Mushroom Swiss Burger",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Beef patty topped with sautéed mushrooms and Swiss cheese. Contains Dairy | Contains Gluten",
                        "categories": [{"id": "#cat-burgers"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-B04",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-B04", "name": "Regular",
                                "sku": "SKU007",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 1600, "currency": "USD"}
                            }
                        }]
                    }
                },

                # ── Sandwiches ────────────────────────────────────────────
                {
                    "type": "ITEM", "id": "#item-SW01",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Grilled Chicken Sandwich",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Grilled chicken breast, lettuce, tomato, honey mustard. Dairy-Free | Contains Gluten | Halal",
                        "categories": [{"id": "#cat-sandwiches"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-SW01",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-SW01", "name": "Regular",
                                "sku": "SKU008",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 1400, "currency": "USD"}
                            }
                        }]
                    }
                },
                {
                    "type": "ITEM", "id": "#item-SW02",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Philly Cheesesteak",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Shaved beef, grilled onions, peppers, melted provolone. Contains Dairy | Contains Gluten",
                        "categories": [{"id": "#cat-sandwiches"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-SW02",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-SW02", "name": "Regular",
                                "sku": "SKU009",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 1600, "currency": "USD"}
                            }
                        }]
                    }
                },
                {
                    "type": "ITEM", "id": "#item-SW03",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Pulled Pork Sandwich",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Slow-smoked pulled pork, coleslaw, BBQ sauce on brioche bun. Dairy-Free | Contains Gluten",
                        "categories": [{"id": "#cat-sandwiches"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-SW03",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-SW03", "name": "Regular",
                                "sku": "SKU010",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 1500, "currency": "USD"}
                            }
                        }]
                    }
                },

                # ── Mains ─────────────────────────────────────────────────
                {
                    "type": "ITEM", "id": "#item-M01",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "BBQ Ribs",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Slow-cooked pork ribs glazed with house BBQ sauce. Gluten-Free | Dairy-Free",
                        "categories": [{"id": "#cat-mains"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-M01",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-M01", "name": "Regular",
                                "sku": "SKU011",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 2800, "currency": "USD"}
                            }
                        }]
                    }
                },
                {
                    "type": "ITEM", "id": "#item-M02",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Fried Chicken Plate",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Southern-style fried chicken served with mashed potatoes and gravy. Contains Dairy | Contains Gluten",
                        "categories": [{"id": "#cat-mains"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-M02",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-M02", "name": "Regular",
                                "sku": "SKU012",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 2000, "currency": "USD"}
                            }
                        }]
                    }
                },
                {
                    "type": "ITEM", "id": "#item-M03",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "New York Strip Steak",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Grilled 12 oz NY strip served with garlic butter and fries. Gluten-Free | Contains Dairy",
                        "categories": [{"id": "#cat-mains"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-M03",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-M03", "name": "Regular",
                                "sku": "SKU013",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 3400, "currency": "USD"}
                            }
                        }]
                    }
                },
                {
                    "type": "ITEM", "id": "#item-M04",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Mac & Cheese",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Creamy baked macaroni with cheddar cheese sauce. Vegetarian | Contains Dairy | Contains Gluten",
                        "categories": [{"id": "#cat-mains"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-M04",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-M04", "name": "Regular",
                                "sku": "SKU014",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 1600, "currency": "USD"}
                            }
                        }]
                    }
                },

                # ── Desserts ──────────────────────────────────────────────
                {
                    "type": "ITEM", "id": "#item-D01",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "New York Cheesecake",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Classic cheesecake with strawberry sauce. Vegetarian | Contains Dairy | Contains Gluten",
                        "categories": [{"id": "#cat-desserts"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-D01",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-D01", "name": "Regular",
                                "sku": "SKU015",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 1000, "currency": "USD"}
                            }
                        }]
                    }
                },
                {
                    "type": "ITEM", "id": "#item-D02",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Chocolate Brownie Sundae",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Warm chocolate brownie topped with vanilla ice cream. Vegetarian | Contains Dairy | Contains Gluten",
                        "categories": [{"id": "#cat-desserts"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-D02",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-D02", "name": "Regular",
                                "sku": "SKU016",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 1100, "currency": "USD"}
                            }
                        }]
                    }
                },
                {
                    "type": "ITEM", "id": "#item-D03",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Apple Pie",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Classic American apple pie served warm. Vegetarian | Contains Dairy | Contains Gluten",
                        "categories": [{"id": "#cat-desserts"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-D03",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-D03", "name": "Regular",
                                "sku": "SKU017",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 900, "currency": "USD"}
                            }
                        }]
                    }
                },

                # ── Drinks ────────────────────────────────────────────────
                {
                    "type": "ITEM", "id": "#item-DR01",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Coca-Cola",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Chilled Coca-Cola served over ice. Vegan | Dairy-Free | Gluten-Free",
                        "categories": [{"id": "#cat-drinks"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-DR01",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-DR01", "name": "Regular",
                                "sku": "SKU018",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 300, "currency": "USD"}
                            }
                        }]
                    }
                },
                {
                    "type": "ITEM", "id": "#item-DR02",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Iced Tea",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Freshly brewed black tea served over ice. Vegan | Dairy-Free | Gluten-Free",
                        "categories": [{"id": "#cat-drinks"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-DR02",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-DR02", "name": "Regular",
                                "sku": "SKU019",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 300, "currency": "USD"}
                            }
                        }]
                    }
                },
                {
                    "type": "ITEM", "id": "#item-DR03",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Lemonade",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Freshly squeezed lemonade, lightly sweetened. Vegan | Dairy-Free | Gluten-Free",
                        "categories": [{"id": "#cat-drinks"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-DR03",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-DR03", "name": "Regular",
                                "sku": "SKU020",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 400, "currency": "USD"}
                            }
                        }]
                    }
                },
                {
                    "type": "ITEM", "id": "#item-DR04",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Craft Beer (Pint)",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Rotating selection of local craft beers on tap. Vegan | Dairy-Free | Contains Gluten",
                        "categories": [{"id": "#cat-drinks"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-DR04",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-DR04", "name": "Regular",
                                "sku": "SKU021",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 700, "currency": "USD"}
                            }
                        }]
                    }
                },
                {
                    "type": "ITEM", "id": "#item-DR05",
                    "present_at_all_locations": True,
                    "item_data": {
                        "name": "Espresso",
                        "product_type": "FOOD_AND_BEV",
                        "description": "Rich double shot of freshly pulled espresso. Vegan | Dairy-Free | Gluten-Free",
                        "categories": [{"id": "#cat-drinks"}],
                        "variations": [{
                            "type": "ITEM_VARIATION", "id": "#var-DR05",
                            "present_at_all_locations": True,
                            "item_variation_data": {
                                "item_id": "#item-DR05", "name": "Regular",
                                "sku": "SKU022",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 400, "currency": "USD"}
                            }
                        }]
                    }
                },

            ]
        }
    ]
)