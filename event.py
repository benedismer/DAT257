"""In-memory event model and sample data for previewing the events page."""

import random
from dataclasses import dataclass
from datetime import date as Date
from datetime import time as Time


@dataclass
class Event:
    """Python representation of one row in the Events table."""

    id: int
    event_name: str
    country: str
    city: str
    time: Time
    date: Date


def add_events(event_name, country, city, time, date):
    """Create an in-memory event without inserting anything into PostgreSQL."""
    return Event(
        id=0,
        event_name=event_name,
        country=country,
        city=city,
        time=time,
        date=date,
    )


def create_sample_events():
    """Return several random events for previewing the HTML page."""
    possible_events = [
        add_events("e1", "Country 1", "City 1", Time(10, 0), Date(2026, 11, 3)),
        add_events("e2", "Country 2", "City 2", Time(9, 30), Date(2026, 10, 14)),
        add_events("e3", "Country 3", "City 3", Time(13, 0), Date(2026, 9, 28)),
        add_events("e4", "Country 4", "City 4", Time(18, 30), Date(2026, 8, 21)),
        add_events("e5", "Country 5", "City 5", Time(17, 0), Date(2026, 12, 5)),
        add_events("e6", "Country 6", "City 6", Time(20, 15), Date(2026, 7, 12)),
        add_events("e7", "Country 7", "City 7", Time(8, 45), Date(2026, 10, 2)),
        add_events("e8", "Country 8", "City 8", Time(11, 30), Date(2026, 6, 19)),
        add_events("e9", "Country 9", "City 9", Time(14, 0), Date(2026, 11, 17)),
        add_events("e10", "Country 10", "City 10", Time(10, 30), Date(2026, 5, 8)),
        add_events("e11", "Country 11", "City 11", Time(9, 0), Date(2026, 9, 9)),
        add_events("e12", "Country 12", "City 12", Time(16, 0), Date(2026, 4, 23)),
        add_events("e13", "Country 13", "City 13", Time(12, 15), Date(2026, 8, 6)),
        add_events("e14", "Country 14", "City 14", Time(18, 0), Date(2026, 3, 14)),
        add_events("e15", "Country 15", "City 15", Time(9, 15), Date(2026, 12, 12)),
        add_events("e16", "Country 16", "City 16", Time(15, 30), Date(2026, 7, 30)),
        add_events("e17", "Country 17", "City 17", Time(19, 0), Date(2026, 10, 26)),
        add_events("e18", "Country 18", "City 18", Time(10, 45), Date(2026, 6, 7)),
        add_events("e19", "Australia", "Melbourne", Time(21, 0), Date(2026, 11, 28)),
        add_events("e20", "Country 20", "City 20", Time(13, 45), Date(2026, 2, 18)),
    ]

    random_events = random.sample(possible_events, k=16)
    for event_id, event in enumerate(random_events, start=1):
        event.id = event_id
    return random_events
