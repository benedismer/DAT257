"""Trash location model used by the map."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TrashLocation:
    id: int
    latitude: float
    longitude: float
    created_at: datetime | None = None

    def as_dict(self):
        return {
            "id": self.id,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }
