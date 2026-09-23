-- ============================================================================
--  Database schema (structure only — no data, no application logic).
--
--  This file defines the tables the app needs. It is the single source of
--  truth for the database layout.
--
-- ============================================================================

-- Example starter table (from the events feature). Adjust to your needs.
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_name TEXT,
    country    TEXT,
    city       TEXT,
    time       TIME,
    date       DATE
);
