# data/policies_data.py
# Hard-coded policies. Later: query DB by restaurant_id.

POLICIES = {
    "reservations": "Reservations can be booked by phone or through this voice agent. Bookings are accepted up to 30 days in advance, including same-day reservations based on availability. Reservations are held for 15 minutes past the scheduled time.",
    "takeout_pickup": "Takeout pickup is available daily from 12:00 PM to 9:30 PM (last order 30 minutes before close). Estimated wait time is 20–35 minutes depending on kitchen volume. Payment methods accepted: credit card, debit card, or cash on pickup. Substitutions and allergy accommodations can be requested when placing the order.",
    "dress_code": "Smart casual. No athletic wear or open-toed shoes for dinner service.",
    "children": "Children are welcome. High chairs and booster seats available on request.",
    "outside_beverages": "No outside beverages permitted.",
    "corkage_fee": "$25 per bottle for wine brought from outside.",
    "pets": "Leashed dogs welcome on the outdoor patio only.",
    "accessibility": "Fully wheelchair accessible. Please inform us in advance for seating arrangements.",
    "payment_methods": "Visa, Mastercard, Amex, Discover, cash",
    "gratuity": "18% gratuity added automatically for parties of 6 or more.",
    "gift_cards": "Available for purchase in-restaurant only",
    "private_events": "Private dining room seats up to 30 guests. Contact the manager at least 2 weeks in advance."
}