"""In-memory event model and sample data for previewing the events page."""

import random
from dataclasses import dataclass
from dataclasses import field
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
    team: str = ""
    attendees: list[str] = field(default_factory=list)


def add_events(event_name, country, city, time, date, team="", attendees=None):
    """Create an in-memory event without inserting anything into PostgreSQL."""
    return Event(
        id=0,
        event_name=event_name,
        country=country,
        city=city,
        time=time,
        date=date,
        team=team,
        attendees=list(attendees or []),
    )


def event_to_row(event):
    """Convert an in-memory event to the row shape used by List.html."""
    return (
        event.id,
        event.event_name,
        event.country,
        event.city,
        event.time.isoformat(timespec="minutes"),
        event.date.isoformat(),
        None,
        None,
    )
