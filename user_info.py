"""In-memory user information model."""

from dataclasses import dataclass, field

from event import Event


@dataclass
class UserInfo:
    """Python representation of a user's basic information."""

    id: int
    username: str
    friends_list: list[str] = field(default_factory=list)
    events_attending: list[Event] = field(default_factory=list)


def add_user_info(username, friends_list=None, events_attending=None):
    """Create an in-memory user info object without inserting anything into PostgreSQL."""
    return UserInfo(
        id=0,
        username=username,
        friends_list=list(friends_list or []),
        events_attending=list(events_attending or []),
    )
