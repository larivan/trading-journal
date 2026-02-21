# db/_normalize.py — shared payload normalization helpers for DB modules
from datetime import date, datetime, time
from typing import Any


def normalize_date(value: Any) -> str:
    """Convert a date/datetime/str value to ISO date string (YYYY-MM-DD)."""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def normalize_time(value: Any) -> str:
    """Convert a time/datetime/str value to HH:MM:SS string."""
    if isinstance(value, (time, datetime)):
        return value.strftime("%H:%M:%S")
    return str(value)


def coerce_int(key: str, value: Any) -> int:
    """Coerce value to int, raising ValueError with field name on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be an integer.")


def coerce_float(key: str, value: Any) -> float:
    """Coerce value to float, raising ValueError with field name on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a number.")
