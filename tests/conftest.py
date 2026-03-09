# tests/conftest.py — Test fixtures for database tests
import os
import sqlite3
import tempfile
from typing import Generator

import pytest


@pytest.fixture(scope="function")
def temp_db() -> Generator[str, None, None]:
    """Create a temporary database for each test."""
    # Create temp file
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Patch the DB_PATH in connection module
    import db.connection as conn_module
    original_path = conn_module.DB_PATH
    conn_module.DB_PATH = path
    conn_module._db_initialized = False  # force re-init for fresh temp DB

    # Initialize schema
    from db import init_db
    init_db()

    yield path

    # Restore and cleanup
    conn_module.DB_PATH = original_path
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def db_conn(temp_db: str) -> Generator[sqlite3.Connection, None, None]:
    """Get a connection to the temp database."""
    from db.connection import get_conn
    conn = get_conn()
    yield conn
    conn.close()


@pytest.fixture
def test_user(temp_db) -> int:
    """Create a test user and return user_id."""
    from db.users import create_user
    user_id = create_user("testuser", "hashed_password_placeholder")
    return user_id


@pytest.fixture
def page_app(test_user):
    """Factory fixture: returns callable that creates AppTest for a given page."""
    from db.users import get_user_settings
    from streamlit.testing.v1 import AppTest

    user_id = test_user
    settings = get_user_settings(user_id)

    def factory(page_path: str) -> AppTest:
        at = AppTest.from_file(page_path)
        at.session_state["user_id"] = user_id
        at.session_state["user_settings"] = settings or {}
        return at

    return factory
