# utils/backup.py — Database backup utilities
import shutil
from datetime import datetime
from pathlib import Path

from db.connection import DB_PATH, BASE_DIR

BACKUP_DIR = Path(BASE_DIR) / "backups"
MAX_BACKUPS = 10


def create_backup() -> Path:
    """Create a timestamped backup of the database. Returns backup path."""
    BACKUP_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = BACKUP_DIR / f"journal_backup_{ts}.db"
    shutil.copy2(DB_PATH, dst)
    _rotate_backups()
    return dst


def _rotate_backups() -> None:
    """Keep only the MAX_BACKUPS most recent backups."""
    backups = sorted(BACKUP_DIR.glob("journal_backup_*.db"))
    for old in backups[:-MAX_BACKUPS]:
        old.unlink(missing_ok=True)


def list_backups() -> list[Path]:
    """Return list of backup files sorted newest first."""
    if not BACKUP_DIR.exists():
        return []
    return sorted(BACKUP_DIR.glob("journal_backup_*.db"), reverse=True)


def get_backup_bytes(path: Path) -> bytes:
    """Read backup file as bytes for download."""
    return path.read_bytes()
