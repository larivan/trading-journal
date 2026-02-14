# utils/date_periods.py — Shared date range calculation
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional, Tuple


def compute_date_range(period_key: str) -> Optional[Tuple[date, date]]:
    """
    Compute a (start, end) date range for a given period key.

    Supported keys:
        today, week, month, quarter, year

    Returns None for unrecognized keys (e.g. 'custom').
    """
    today = date.today()

    if period_key == "today":
        return (today, today)
    if period_key == "week":
        return (today - timedelta(days=today.weekday()), today)
    if period_key == "month":
        return (today.replace(day=1), today)
    if period_key == "quarter":
        quarter = (today.month - 1) // 3
        quarter_start_month = quarter * 3 + 1
        return (today.replace(month=quarter_start_month, day=1), today)
    if period_key == "year":
        return (today.replace(month=1, day=1), today)

    return None
