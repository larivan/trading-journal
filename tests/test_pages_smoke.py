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


def test_settings_renders(page_app):
    at = page_app("pages/settings.py")
    at.run()
    assert not at.exception
