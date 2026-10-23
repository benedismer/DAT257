"""Picture model and storage location."""

from dataclasses import dataclass
from pathlib import Path


PICTURE_FOLDER = Path(__file__).resolve().parent.parent / "pictures"
PICTURE_SUFFIXES = {".gif", ".jpeg", ".jpg", ".png", ".webp"}


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


def dummy_pictures_for_event(event_id):
    """Return all local dummy pictures for any event."""
    pictures = []
    for picture_id, path in enumerate(sorted(PICTURE_FOLDER.iterdir()), start=1):
        if path.is_file() and path.suffix.lower() in PICTURE_SUFFIXES:
            pictures.append(
                Picture(
                    id=picture_id,
                    file_path=path.name,
                    uploader_id=1,
                    event_id=event_id,
                )
            )
    return pictures


def dummy_pictures_for_user(uploader_id):
    """Return all local dummy pictures attributed to one user."""
    pictures = []
    for picture_id, path in enumerate(sorted(PICTURE_FOLDER.iterdir()), start=1):
        if path.is_file() and path.suffix.lower() in PICTURE_SUFFIXES:
            pictures.append(
                Picture(
                    id=picture_id,
                    file_path=path.name,
                    uploader_id=uploader_id,
                    event_id=0,
                )
            )
    return pictures


def dummy_pictures_for_team(team_id):
    """Return all local dummy pictures attributed to one team."""
    pictures = []
    for picture_id, path in enumerate(sorted(PICTURE_FOLDER.iterdir()), start=1):
        if path.is_file() and path.suffix.lower() in PICTURE_SUFFIXES:
            pictures.append(
                Picture(
                    id=picture_id,
                    file_path=path.name,
                    uploader_id=0,
                    event_id=0,
                    team_id=team_id,
                )
            )
    return pictures
