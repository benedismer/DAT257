"""Picture model and storage location."""

from dataclasses import dataclass
from pathlib import Path


PICTURE_FOLDER = Path(__file__).resolve().parent / "pictures"


@dataclass
class Picture:
    """Python representation of an uploaded event picture."""

    id: int
    file_path: Path
    uploader_id: int
    event_id: int
    team_id: int | None = None

    @property
    def absolute_path(self) -> Path:
        """Return the picture path inside the project's picture folder."""
        return PICTURE_FOLDER / self.file_path


def add_picture(file_path, uploader_id, event_id, team_id=None):
    """Create picture metadata without inserting anything into PostgreSQL."""
    return Picture(
        id=0,
        file_path=Path(file_path),
        uploader_id=uploader_id,
        event_id=event_id,
        team_id=team_id,
    )
