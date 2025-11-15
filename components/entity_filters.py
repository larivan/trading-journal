"""Общие вспомогательные функции для фильтров сущностей."""

from datetime import date, timedelta
from typing import Dict, Optional, Tuple

from db import list_accounts

TAB_DEFINITIONS = [
    ("Today", "today"),
    ("Current week", "week"),
    ("Current month", "month"),
    ("Current quarter", "quarter"),
    ("Current year", "year"),
    ("Custom", "custom"),
]


def tab_date_range(tab_key: str) -> Tuple[Optional[date], Optional[date]]:
    """Возвращает диапазон дат для предопределённых вкладок."""
    today = date.today()
    if tab_key == "today":
        return today, today
    if tab_key == "week":
        week_start = today - timedelta(days=today.weekday())
        return week_start, today
    if tab_key == "month":
        month_start = today.replace(day=1)
        return month_start, today
    if tab_key == "quarter":
        quarter = (today.month - 1) // 3
        quarter_start_month = quarter * 3 + 1
        quarter_start = today.replace(month=quarter_start_month, day=1)
        return quarter_start, today
    if tab_key == "year":
        year_start = today.replace(month=1, day=1)
        return year_start, today
    return None, None


def ensure_custom_range(
    initial_range: Optional[Tuple[Optional[date], Optional[date]]],
    *,
    days_back: int = 7,
) -> Tuple[date, date]:
    """Гарантирует корректный диапазон дат для таба Custom."""
    today = date.today()
    default_from = today - timedelta(days=days_back)
    default_to = today
    if not initial_range:
        return default_from, default_to
    start, end = initial_range
    if isinstance(start, date):
        default_from = start
    if isinstance(end, date):
        default_to = end
    return default_from, default_to
