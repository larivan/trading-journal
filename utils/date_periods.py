# utils/date_periods.py — Shared date range calculation
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, Tuple


def today_in_tz(tz_name: Optional[str]) -> date:
    """Return today's date in the given timezone (supports ZoneInfo names and UTC+N format)."""
    if not tz_name:
        return date.today()
    try:
        from utils.trade_sessions import _resolve_tz
        tz = _resolve_tz(tz_name)
        return datetime.now(tz).date()
    except Exception:
        return date.today()


def compute_date_range(
    period_key: str,
    tz_name: Optional[str] = None,
) -> Optional[Tuple[date, date]]:
    """
    Compute a (start, end) date range for a given period key.

    Supported keys:
        today, week, month, quarter, year

    Returns None for unrecognized keys (e.g. 'custom').
    If tz_name is provided, "today" is computed in that timezone.
    """
    today = today_in_tz(tz_name)

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
