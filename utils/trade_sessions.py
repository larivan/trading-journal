"""Вспомогательные функции для расчёта торговых сессий."""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, Sequence, Tuple, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from config import LOCAL_TZ, TRADE_SESSION_VALUES

DateLike = Union[date, datetime, str]
TimeLike = Union[time, datetime, str]

FRANKFURT_TZ = ZoneInfo("Europe/Berlin")
LONDON_TZ = ZoneInfo("Europe/London")
NEW_YORK_TZ = ZoneInfo("America/New_York")

SessionWindow = Tuple[str, time, time]

FRANKFURT_WINDOWS: Sequence[SessionWindow] = (
    ("Frankfurt", time(8, 0), time(9, 0)),
)

LONDON_WINDOWS: Sequence[SessionWindow] = (
    ("LOKZ", time(8, 0), time(10, 0)),
    ("Lunch", time(10, 0), time(12, 0)),
)

NEW_YORK_WINDOWS: Sequence[SessionWindow] = (
    ("NYKZ", time(8, 0), time(10, 0)),
    ("Pre-NY", time(7, 0), time(8, 0)),
)


def detect_trade_session(
    date_value: DateLike,
    time_value: TimeLike,
    *,
    local_tz_label: Optional[str] = None,
) -> str:
    """Определяет торговую сессию на основании локального времени сделки."""

    local_dt = _make_local_datetime(
        date_value,
        time_value,
        local_tz_label or LOCAL_TZ,
    )

    for tzinfo, windows in (
        (LONDON_TZ, LONDON_WINDOWS),
        (FRANKFURT_TZ, FRANKFURT_WINDOWS),
        (NEW_YORK_TZ, NEW_YORK_WINDOWS),
    ):
        session = _detect_by_windows(local_dt, tzinfo, windows)
        if session:
            return session

    return "Other" if "Other" in TRADE_SESSION_VALUES else TRADE_SESSION_VALUES[-1]


def _detect_by_windows(
    localized_dt: datetime,
    target_tz: ZoneInfo,
    windows: Sequence[SessionWindow],
) -> Optional[str]:
    target_time = localized_dt.astimezone(target_tz).time()
    for session_name, start, end in windows:
        if _in_window(target_time, start, end):
            return session_name
    return None


def _in_window(moment: time, start: time, end: time) -> bool:
    """Проверяет попадание момента времени в интервал [start; end)."""
    if start <= end:
        return start <= moment < end
    return moment >= start or moment < end


def _make_local_datetime(
    date_value: DateLike,
    time_value: TimeLike,
    local_tz_label: str,
) -> datetime:
    date_part = _ensure_date(date_value)
    time_part = _ensure_time(time_value)
    tzinfo = _resolve_tz(local_tz_label)
    naive_time = time(hour=time_part.hour, minute=time_part.minute, second=time_part.second)
    return datetime.combine(date_part, naive_time, tzinfo=tzinfo)


def _ensure_date(value: DateLike) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    raise ValueError(f"Unsupported date value: {value!r}")


def _ensure_time(value: TimeLike) -> time:
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                continue
    raise ValueError(f"Unsupported time value: {value!r}")


def _resolve_tz(label: str):
    try:
        return ZoneInfo(label)
    except ZoneInfoNotFoundError:
        pass
    except Exception:
        pass

    match = re.fullmatch(r"UTC([+-]?)(\d{1,2})(?::?(\d{2}))?", label.strip())
    if not match:
        raise ValueError(f"Unsupported timezone label: {label!r}")

    sign = -1 if match.group(1) == "-" else 1
    hours = int(match.group(2))
    minutes = int(match.group(3) or 0)
    delta = timedelta(hours=hours, minutes=minutes) * sign
    return timezone(delta)
