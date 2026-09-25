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
