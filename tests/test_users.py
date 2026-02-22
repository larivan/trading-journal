# tests/test_users.py — Unit tests for db/users.py
import pytest
from db.users import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_settings,
    update_user_settings,
    list_users,
)


class TestCreateUser:
    def test_create_user_basic(self, temp_db):
        user_id = create_user(email="alice@example.com")
        assert user_id is not None
        assert user_id > 0

    def test_create_user_with_username(self, temp_db):
        user_id = create_user(email="bob@example.com", username="bob")
        user = get_user_by_id(user_id)
        assert user["email"] == "bob@example.com"
        assert user["username"] == "bob"

    def test_create_duplicate_email_raises(self, temp_db):
        import sqlite3
        create_user(email="charlie@example.com")
        with pytest.raises((sqlite3.IntegrityError, Exception)):
            create_user(email="charlie@example.com")

    def test_create_user_returns_incremental_ids(self, temp_db):
        id1 = create_user(email="user1@example.com")
        id2 = create_user(email="user2@example.com")
        assert id2 > id1

    def test_create_user_initializes_settings(self, temp_db):
        user_id = create_user(email="dave@example.com")
        settings = get_user_settings(user_id)
        assert isinstance(settings, dict)
        assert "be_threshold" in settings
        assert "risk_min" in settings
        assert "risk_max" in settings


class TestGetUser:
    def test_get_by_email(self, temp_db):
        create_user(email="eve@example.com", username="eve")
        user = get_user_by_email("eve@example.com")
        assert user is not None
        assert user["email"] == "eve@example.com"

    def test_get_by_email_nonexistent(self, temp_db):
        user = get_user_by_email("nonexistent@example.com")
        assert user is None

    def test_get_by_id(self, temp_db):
        user_id = create_user(email="frank@example.com", username="frank")
        user = get_user_by_id(user_id)
        assert user is not None
        assert user["id"] == user_id
        assert user["username"] == "frank"

    def test_get_by_id_nonexistent(self, temp_db):
        user = get_user_by_id(99999)
        assert user is None


class TestUserSettings:
    def test_default_settings(self, temp_db):
        user_id = create_user(email="henry@example.com")
        settings = get_user_settings(user_id)
        assert isinstance(settings.get("assets"), list)
        assert settings["be_threshold"] == pytest.approx(0.05)
        assert settings["risk_min"] == pytest.approx(0.5)
        assert settings["risk_max"] == pytest.approx(2.0)
        assert settings["local_tz"] == "Europe/Moscow"
        assert settings["currency"] == "USD"
        assert settings["language"] == "en"

    def test_update_settings(self, temp_db):
        user_id = create_user(email="ivan@example.com")
        update_user_settings(user_id, {
            "be_threshold": 0.1,
            "currency": "EUR",
        })
        settings = get_user_settings(user_id)
        assert settings["be_threshold"] == pytest.approx(0.1)
        assert settings["currency"] == "EUR"

    def test_update_assets_list(self, temp_db):
        user_id = create_user(email="julia@example.com")
        new_assets = ["BTC/USD", "ETH/USD"]
        update_user_settings(user_id, {"assets": new_assets})
        settings = get_user_settings(user_id)
        assert settings["assets"] == new_assets

    def test_update_ignores_unknown_fields(self, temp_db):
        user_id = create_user(email="kate@example.com")
        update_user_settings(user_id, {
            "unknown_field": "value",
            "risk_min": 0.3,
        })
        settings = get_user_settings(user_id)
        assert settings["risk_min"] == pytest.approx(0.3)
        assert "unknown_field" not in settings

    def test_settings_nonexistent_user(self, temp_db):
        settings = get_user_settings(99999)
        assert isinstance(settings, dict)


class TestListUsers:
    def test_list_empty(self, temp_db):
        users = list_users()
        assert users == []

    def test_list_users(self, temp_db):
        create_user(email="user_a@example.com", username="user_a")
        create_user(email="user_b@example.com", username="user_b")
        users = list_users()
        assert len(users) == 2
        emails = [u["email"] for u in users]
        assert "user_a@example.com" in emails
        assert "user_b@example.com" in emails
