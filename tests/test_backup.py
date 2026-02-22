# tests/test_backup.py — Unit tests for utils/backup.py
from datetime import datetime
from pathlib import Path

import pytest


class _SeqDatetime:
    """Replaces datetime in utils.backup to give unique timestamps per call."""
    _count = 0

    @classmethod
    def now(cls):
        cls._count += 1
        return datetime(2026, 2, 21, 10, 0, cls._count)

    @classmethod
    def reset(cls):
        cls._count = 0


@pytest.fixture
def backup_env(tmp_path, monkeypatch):
    """Patch DB_PATH, BACKUP_DIR and datetime to temporary directories."""
    # Create a fake DB file
    fake_db = tmp_path / "test_journal.db"
    fake_db.write_bytes(b"SQLite test data")

    backup_dir = tmp_path / "backups"

    import utils.backup as backup_module

    # Reset the sequential timestamp counter
    _SeqDatetime.reset()

    # Patch the module-level variable in utils.backup directly
    monkeypatch.setattr(backup_module, "DB_PATH", str(fake_db))
    monkeypatch.setattr(backup_module, "BACKUP_DIR", backup_dir)
    monkeypatch.setattr(backup_module, "datetime", _SeqDatetime)

    yield {
        "db_path": fake_db,
        "backup_dir": backup_dir,
        "backup_module": backup_module,
    }


class TestCreateBackup:
    def test_creates_backup_file(self, backup_env):
        from utils.backup import create_backup
        path = create_backup()
        assert path.exists()
        assert path.suffix == ".db"
        assert "journal_backup_" in path.name

    def test_backup_content_matches_source(self, backup_env):
        from utils.backup import create_backup
        path = create_backup()
        assert path.read_bytes() == b"SQLite test data"

    def test_backup_dir_created(self, backup_env):
        from utils.backup import create_backup
        backup_dir = backup_env["backup_dir"]
        assert not backup_dir.exists()
        create_backup()
        assert backup_dir.exists()


class TestRotateBackups:
    def test_rotation_keeps_max_backups(self, backup_env):
        """After MAX_BACKUPS+3 backups, only MAX_BACKUPS remain."""
        import utils.backup as bm
        original_max = bm.MAX_BACKUPS
        bm.MAX_BACKUPS = 3

        try:
            from utils.backup import create_backup, list_backups
            for _ in range(6):
                create_backup()
            remaining = list_backups()
            assert len(remaining) == 3
        finally:
            bm.MAX_BACKUPS = original_max

    def test_rotation_keeps_newest(self, backup_env):
        """Rotation keeps the most recent backups."""
        import utils.backup as bm
        original_max = bm.MAX_BACKUPS
        bm.MAX_BACKUPS = 2

        try:
            from utils.backup import create_backup, list_backups
            p1 = create_backup()
            p2 = create_backup()
            p3 = create_backup()  # p1 should be rotated out

            remaining = list_backups()
            remaining_names = {p.name for p in remaining}
            assert p1.name not in remaining_names
            assert p2.name in remaining_names
            assert p3.name in remaining_names
        finally:
            bm.MAX_BACKUPS = original_max


class TestListBackups:
    def test_list_empty(self, backup_env):
        from utils.backup import list_backups
        assert list_backups() == []

    def test_list_returns_paths(self, backup_env):
        from utils.backup import create_backup, list_backups
        create_backup()
        create_backup()
        backups = list_backups()
        assert len(backups) == 2
        assert all(isinstance(p, Path) for p in backups)

    def test_list_ordered_newest_first(self, backup_env):
        from utils.backup import create_backup, list_backups
        p1 = create_backup()
        p2 = create_backup()
        backups = list_backups()
        assert len(backups) == 2
        # Newest first — p2 should come before p1
        assert backups[0].name > backups[1].name


class TestGetBackupBytes:
    def test_returns_bytes(self, backup_env):
        from utils.backup import create_backup, get_backup_bytes
        path = create_backup()
        data = get_backup_bytes(path)
        assert isinstance(data, bytes)
        assert data == b"SQLite test data"
