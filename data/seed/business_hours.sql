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