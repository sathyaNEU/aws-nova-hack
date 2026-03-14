-- Run this once to create the business_hours table
CREATE TABLE IF NOT EXISTS business_hours (
    id          SERIAL PRIMARY KEY,
    day_of_week TEXT NOT NULL UNIQUE,   -- 'monday', 'tuesday', etc.
    open_time   TEXT,                   -- '09:00'
    close_time  TEXT,                   -- '17:00'
    is_open     BOOLEAN NOT NULL DEFAULT TRUE
);

-- Seed default data (all days open by default)
INSERT INTO business_hours (day_of_week, open_time, close_time, is_open) VALUES
    ('monday',    '09:00', '17:00', TRUE),
    ('tuesday',   '09:00', '17:00', TRUE),
    ('wednesday', '09:00', '17:00', TRUE),
    ('thursday',  '09:00', '17:00', TRUE),
    ('friday',    '09:00', '17:00', TRUE),
    ('saturday',  '10:00', '15:00', TRUE),
    ('sunday',    '10:00', '15:00', TRUE)
ON CONFLICT (day_of_week) DO NOTHING;

-- policy_information table
CREATE TABLE IF NOT EXISTS policy_information (
    id          SERIAL PRIMARY KEY,
    policy_name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL
);

INSERT INTO policy_information (policy_name, description) VALUES
    ('reservations',       'Reservations can be booked by phone or through this voice agent. Bookings are accepted up to 30 days in advance, including same-day reservations based on availability. Reservations are held for 15 minutes past the scheduled time.'),
    ('takeout_pickup',     'Takeout pickup is available daily from 12:00 PM to 9:30 PM (last order 30 minutes before close). Estimated wait time is 20–35 minutes depending on kitchen volume. Payment methods accepted: credit card, debit card, or cash on pickup. Substitutions and allergy accommodations can be requested when placing the order.'),
    ('dress_code',         'Smart casual. No athletic wear or open-toed shoes for dinner service.'),
    ('children',           'Children are welcome. High chairs and booster seats available on request.'),
    ('outside_beverages',  'No outside beverages permitted.'),
    ('corkage_fee',        '$25 per bottle for wine brought from outside.'),
    ('pets',               'Leashed dogs welcome on the outdoor patio only.'),
    ('accessibility',      'Fully wheelchair accessible. Please inform us in advance for seating arrangements.'),
    ('payment_methods',    'Visa, Mastercard, Amex, Discover, cash.'),
    ('gratuity',           '18% gratuity added automatically for parties of 6 or more.'),
    ('gift_cards',         'Available for purchase in-restaurant only.'),
    ('private_events',     'Private dining room seats up to 30 guests. Contact the manager at least 2 weeks in advance.')
ON CONFLICT (policy_name) DO NOTHING;