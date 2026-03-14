# data/restaurant.py
# Hard-coded restaurant data. Later: query DB by restaurant_id.

RESTAURANT_INFO = {
    "name": "Bella Tavola",
    "address": "142 Oak Street, Brooklyn, NY 11201",
    "phone": "+1 (718) 555-0192",
    "timezone": "America/New_York",
}

PARKING_INFO = {
    "street_parking": {
        "available": True,
        "notes": "Free street parking on Oak Street and Elm Avenue. 2-hour limit Mon–Sat before 6 PM.",
    },
    "nearby_garages": [
        {
            "name": "Atlantic Parking Garage",
            "distance_miles": 0.2,
            "address": "200 Atlantic Ave, Brooklyn, NY",
            "rates": {"hourly": "$5", "evening_flat_after": "5 PM", "evening_flat_price": "$15"},
            "hours": "24/7",
        },
        {
            "name": "Borough Parking",
            "distance_miles": 0.4,
            "address": "310 Fulton St, Brooklyn, NY",
            "rates": {"hourly": "$4", "evening_flat_after": "6 PM", "evening_flat_price": "$12"},
            "hours": "6 AM – midnight",
        },
    ],
    "valet": {
        "available": True,
        "days": ["friday", "saturday"],
        "hours": "6 PM - 11 PM",
        "cost": "$18",
    },
    "accessible_spaces": {
        "available": True,
        "notes": "Two ADA spaces directly in front of the restaurant entrance.",
    },
}