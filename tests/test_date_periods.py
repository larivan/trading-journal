# tests/test_date_periods.py — Tests for compute_date_range()
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from utils.date_periods import compute_date_range


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _quarter_start(d: date) -> date:
    quarter = (d.month - 1) // 3
    return d.replace(month=quarter * 3 + 1, day=1)


class TestComputeDateRange:
    def test_unknown_key_returns_none(self):
        assert compute_date_range("custom") is None
        assert compute_date_range("") is None
        assert compute_date_range("last_week") is None

    def test_today(self):
        today = date.today()
        result = compute_date_range("today")
        assert result == (today, today)

    def test_today_start_le_end(self):
        start, end = compute_date_range("today")
        assert start <= end

    def test_week_starts_on_monday(self):
        today = date.today()
        start, end = compute_date_range("week")
        assert start == _monday(today)
        assert end == today
        assert start.weekday() == 0

    def test_week_start_le_end(self):
        start, end = compute_date_range("week")
        assert start <= end

    def test_month_starts_on_first(self):
        today = date.today()
        start, end = compute_date_range("month")
        assert start == today.replace(day=1)
        assert end == today

    def test_month_start_le_end(self):
        start, end = compute_date_range("month")
        assert start <= end

    def test_quarter_starts_on_correct_month(self):
        today = date.today()
        start, end = compute_date_range("quarter")
        assert start == _quarter_start(today)
        assert start.day == 1
        assert end == today

    def test_quarter_start_le_end(self):
        start, end = compute_date_range("quarter")
        assert start <= end

    def test_year_starts_on_jan_1(self):
        today = date.today()
        start, end = compute_date_range("year")
        assert start == today.replace(month=1, day=1)
        assert end == today

    def test_year_start_le_end(self):
        start, end = compute_date_range("year")
        assert start <= end

    @pytest.mark.parametrize("period", ["today", "week", "month", "quarter", "year"])
    def test_all_periods_return_tuple(self, period):
        result = compute_date_range(period)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_week_on_monday(self):
        """На понедельник начало недели == сегодня."""
        monday = date(2026, 2, 16)  # понедельник
        with patch("utils.date_periods.date") as mock_date:
            mock_date.today.return_value = monday
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            start, end = compute_date_range("week")
        assert start == monday
        assert end == monday

    def test_quarter_q1(self):
        """Первый квартал — начало 1 января."""
        jan = date(2026, 1, 15)
        with patch("utils.date_periods.date") as mock_date:
            mock_date.today.return_value = jan
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            start, _ = compute_date_range("quarter")
        assert start == date(2026, 1, 1)

    def test_quarter_q3(self):
        """Третий квартал — начало 1 июля."""
        aug = date(2026, 8, 10)
        with patch("utils.date_periods.date") as mock_date:
            mock_date.today.return_value = aug
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            start, _ = compute_date_range("quarter")
        assert start == date(2026, 7, 1)
