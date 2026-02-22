# tests/test_users.py — Unit tests for db/users.py
import pytest
from db.users import (
    create_user,
    get_user_by_username,
    get_user_by_id,
    update_user_password,
    get_user_settings,
    update_user_settings,
    list_users,
    count_users,
)


class TestCreateUser:
    def test_create_user_basic(self, temp_db):
        user_id = create_user("alice", "hashed_pw_1")
        assert user_id is not None
        assert user_id > 0

    def test_create_user_with_email(self, temp_db):
        user_id = create_user("bob", "hashed_pw_2", email="bob@example.com")
        user = get_user_by_id(user_id)
        assert user["email"] == "bob@example.com"

    def test_create_duplicate_username_raises(self, temp_db):
        import sqlite3
        create_user("charlie", "hash1")
        with pytest.raises((sqlite3.IntegrityError, Exception)):
            create_user("charlie", "hash2")

    def test_create_user_returns_incremental_ids(self, temp_db):
        id1 = create_user("user1", "hash1")
        id2 = create_user("user2", "hash2")
        assert id2 > id1

    def test_create_user_initializes_settings(self, temp_db):
        user_id = create_user("dave", "hash")
        settings = get_user_settings(user_id)
        assert isinstance(settings, dict)
        # Default settings should exist
        assert "be_threshold" in settings
        assert "risk_min" in settings
        assert "risk_max" in settings


class TestGetUser:
    def test_get_by_username(self, temp_db):
        create_user("eve", "hashed")
        user = get_user_by_username("eve")
        assert user is not None
        assert user["username"] == "eve"

    def test_get_by_username_nonexistent(self, temp_db):
        user = get_user_by_username("nonexistent")
        assert user is None

    def test_get_by_id(self, temp_db):
        user_id = create_user("frank", "hashed")
        user = get_user_by_id(user_id)
        assert user is not None
        assert user["id"] == user_id
        assert user["username"] == "frank"

    def test_get_by_id_nonexistent(self, temp_db):
        user = get_user_by_id(99999)
        assert user is None


class TestUpdateUserPassword:
    def test_update_password(self, temp_db):
        user_id = create_user("grace", "old_hash")
        update_user_password(user_id, "new_hash")
        user = get_user_by_id(user_id)
        assert user["password_hash"] == "new_hash"


class TestUserSettings:
    def test_default_settings(self, temp_db):
        user_id = create_user("henry", "hash")
        settings = get_user_settings(user_id)
        assert isinstance(settings.get("assets"), list)
        assert settings["be_threshold"] == pytest.approx(0.05)
        assert settings["risk_min"] == pytest.approx(0.5)
        assert settings["risk_max"] == pytest.approx(2.0)
        assert settings["local_tz"] == "Europe/Moscow"
        assert settings["currency"] == "USD"
        assert settings["language"] == "en"

    def test_update_settings(self, temp_db):
        user_id = create_user("ivan", "hash")
        update_user_settings(user_id, {
            "be_threshold": 0.1,
            "currency": "EUR",
        })
        settings = get_user_settings(user_id)
        assert settings["be_threshold"] == pytest.approx(0.1)
        assert settings["currency"] == "EUR"

    def test_update_assets_list(self, temp_db):
        user_id = create_user("julia", "hash")
        new_assets = ["BTC/USD", "ETH/USD"]
        update_user_settings(user_id, {"assets": new_assets})
        settings = get_user_settings(user_id)
        assert settings["assets"] == new_assets

    def test_update_ignores_unknown_fields(self, temp_db):
        user_id = create_user("kate", "hash")
        update_user_settings(user_id, {
            "unknown_field": "value",
            "risk_min": 0.3,
        })
        settings = get_user_settings(user_id)
        assert settings["risk_min"] == pytest.approx(0.3)
        assert "unknown_field" not in settings

    def test_settings_nonexistent_user(self, temp_db):
        # get_user_settings returns defaults even for non-existent user_id
        settings = get_user_settings(99999)
        assert isinstance(settings, dict)


class TestListUsers:
    def test_list_empty(self, temp_db):
        users = list_users()
        assert users == []

    def test_list_users(self, temp_db):
        create_user("user_a", "hash1")
        create_user("user_b", "hash2")
        users = list_users()
        assert len(users) == 2
        usernames = [u["username"] for u in users]
        assert "user_a" in usernames
        assert "user_b" in usernames

    def test_count_users(self, temp_db):
        assert count_users() == 0
        create_user("one", "hash")
        assert count_users() == 1
        create_user("two", "hash")
        assert count_users() == 2
