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


_SQLITE_MAGIC = b"SQLite format 3\x00"


def validate_backup_file(data: bytes) -> bool:
    """Return True if data starts with the SQLite file header."""
    return data[:16] == _SQLITE_MAGIC


def maybe_create_daily_backup() -> None:
    """Create a backup at most once per calendar day (auto-backup on startup)."""
    from datetime import date
    existing = list_backups()
    if existing:
        try:
            ts = datetime.strptime(
                existing[0].stem.replace("journal_backup_", ""), "%Y%m%d_%H%M%S"
            )
            if ts.date() >= date.today():
                return  # уже есть бекап за сегодня
        except ValueError:
            pass
    create_backup()
