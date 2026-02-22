# tests/test_pages_smoke.py — Smoke tests for UI pages
import pytest


def test_dashboard_renders(page_app):
    at = page_app("pages/dashboard.py")
    at.run()
    assert not at.exception


def test_trades_renders(page_app):
    at = page_app("pages/trades.py")
    at.run()
    assert not at.exception


def test_analysis_renders(page_app):
    at = page_app("pages/analysis.py")
    at.run()
    assert not at.exception


def test_notes_renders(page_app):
    at = page_app("pages/notes.py")
    at.run()
    assert not at.exception


def test_setups_renders(page_app):
    at = page_app("pages/setups.py")
    at.run()
    assert not at.exception


def test_settings_accounts_renders(page_app):
    at = page_app("pages/settings_accounts.py")
    at.run()
    assert not at.exception


def test_settings_profile_renders(page_app):
    at = page_app("pages/settings_profile.py")
    at.run()
    assert not at.exception


def test_settings_journal_setup_renders(page_app):
    at = page_app("pages/settings_journal_setup.py")
    at.run()
    assert not at.exception


def test_settings_preferences_renders(page_app):
    at = page_app("pages/settings_preferences.py")
    at.run()
    assert not at.exception


def test_settings_backup_renders():
    """settings_backup.py не читает user_id — тестируем без page_app."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("pages/settings_backup.py")
    at.run()
    assert not at.exception
