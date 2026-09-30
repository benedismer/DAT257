"""Dummy account and events for previewing user event pages."""

from datetime import date, time, timedelta

from event import Event
from user_info import UserInfo


DEMO_USER = UserInfo(
    id=1,
    username="alex",
    friends_list=["sam", "robin", "Green Crew"],
    events_attending=[
        Event(
            id=101,
            event_name="Saturday river cleanup",
            country="Sweden",
            city="Gothenburg",
            time=time(10, 0),
            date=date.today() + timedelta(days=3),
            organizer="Green Crew",
            attendees=["alex", "sam", "robin"],
        ),
        Event(
            id=102,
            event_name="Park sorting session",
            country="Sweden",
            city="Gothenburg",
            time=time(14, 30),
            date=date.today() + timedelta(days=10),
            organizer="Alex",
            attendees=["alex", "casey"],
        ),
        Event(
            id=105,
            event_name="Autumn park cleanup",
            country="Sweden",
            city="Gothenburg",
            time=time(13, 0),
            date=date.today() - timedelta(days=7),
            organizer="Green Crew",
            attendees=["alex", "sam"],
        ),
    ],
    events_created=[
        Event(
            id=106,
            event_name="Neighborhood recycling day",
            country="Sweden",
            city="Gothenburg",
            time=time(12, 0),
            date=date.today() + timedelta(days=21),
            organizer="alex",
            attendees=["alex", "robin"],
        ),
    ],
)


DEMO_ORGANIZER_EVENTS = [
    *DEMO_USER.events_attending,
    Event(
        id=103,
        event_name="Canal cleanup morning",
        country="Sweden",
        city="Gothenburg",
        time=time(9, 0),
        date=date.today() + timedelta(days=17),
        organizer="Green Crew",
        attendees=["sam"],
    ),
    Event(
        id=104,
        event_name="Unaffiliated cleanup",
        country="Sweden",
        city="Gothenburg",
        time=time(11, 0),
        date=date.today() + timedelta(days=5),
        organizer="Other Organizer",
        attendees=[],
    ),
    DEMO_USER.events_attending[-1],
]