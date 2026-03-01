"""Кешированные обёртки над db/ и вспомогательные функции Python-фильтрации.

Стратегия:
- Грузим полный список один раз, кешируем на уровне приложения (ttl=3600).
- Фильтруем в Python — мгновенно для объёмов < 1000 записей.
- Явно сбрасываем кеш через st.cache_data.clear() после любой мутации.
- user_id=None → пустой список без DB-запроса (защита от раннего рендера).
"""

import logging
import time
from typing import Any, Dict, List, Optional

import streamlit as st

from config import BE_THRESHOLD
from db import (
    list_accounts,
    list_analysis,
    list_notes,
    list_setups,
    list_trades,
)

_log = logging.getLogger("cache")

_page_timers: dict = {}


def page_mark(page: str, step: str) -> None:
    """Ставит временну́ю метку и пишет в лог.

    Использование в странице:
        from utils.cached_data import page_mark
        page_mark("trades", "start")
        ...
        page_mark("trades", "data_loaded")
        ...
        page_mark("trades", "done")
    """
    now = time.perf_counter()
    key = f"{page}:start"
    if step == "start":
        _page_timers[key] = now
        _log.warning("[PAGE] %-12s %-20s", page, step)
    else:
        t0 = _page_timers.get(key, now)
        _log.warning("[PAGE] %-12s %-20s +%.0f ms", page, step, (now - t0) * 1000)


def _timed(label: str, fn, *args, **kwargs):
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    ms = (time.perf_counter() - t0) * 1000
    n = len(result) if isinstance(result, list) else "?"
    _log.warning("[DB] %-35s %s rows  %.0f ms", label, n, ms)
    return result


# ---------------------------------------------------------------------------
# Кешированные обёртки
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def cached_trades(user_id: int) -> List[Dict[str, Any]]:
    if user_id is None:
        return []
    return _timed(f"list_trades(user={user_id})", list_trades, user_id)


@st.cache_data(ttl=3600)
def cached_accounts(user_id: int, include_archived: bool = False) -> List[Dict[str, Any]]:
    if user_id is None:
        return []
    return _timed(f"list_accounts(user={user_id}, arch={include_archived})", list_accounts, user_id, include_archived)


@st.cache_data(ttl=3600)
def cached_setups(user_id: int) -> List[Dict[str, Any]]:
    if user_id is None:
        return []
    return _timed(f"list_setups(user={user_id})", list_setups, user_id)


@st.cache_data(ttl=3600)
def cached_analysis(user_id: int) -> List[Dict[str, Any]]:
    if user_id is None:
        return []
    return _timed(f"list_analysis(user={user_id})", list_analysis, user_id)


@st.cache_data(ttl=3600)
def cached_notes(user_id: int) -> List[Dict[str, Any]]:
    if user_id is None:
        return []
    return _timed(f"list_notes(user={user_id})", list_notes, user_id)


# ---------------------------------------------------------------------------
# Python-фильтрация (работает с результатами cached_*)
# ---------------------------------------------------------------------------

def filter_trades(
    rows: List[Dict[str, Any]],
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Фильтрует список трейдов в Python.

    Поддерживаемые ключи filters:
      date_from, date_to  — строки ISO (date_local >= / <=)
      account_id          — int
      state               — str
      asset               — str
      session             — str
      estimation          — int (0 или 1)
      is_missed           — int (0 или 1)
      result              — "Win" | "Loss" | "BE" | "Miss"
    """
    if not filters:
        return rows

    result = []
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    account_id = filters.get("account_id")
    state = filters.get("state")
    asset = filters.get("asset")
    session = filters.get("session")
    estimation = filters.get("estimation")
    is_missed_f = filters.get("is_missed")
    result_f = filters.get("result")

    for row in rows:
        if date_from and (row.get("date_local") or "") < date_from:
            continue
        if date_to and (row.get("date_local") or "") > date_to:
            continue
        if account_id is not None and row.get("account_id") != account_id:
            continue
        if state is not None and row.get("state") != state:
            continue
        if asset is not None and row.get("asset") != asset:
            continue
        if session is not None and row.get("session") != session:
            continue
        if estimation is not None and row.get("estimation") != estimation:
            continue
        if is_missed_f is not None and row.get("is_missed") != is_missed_f:
            continue
        if result_f is not None:
            try:
                rr = float(row.get("risk_reward") or 0)
            except (TypeError, ValueError):
                rr = 0.0
            missed = row.get("is_missed", 0)
            if result_f == "Win":
                if not (rr > BE_THRESHOLD and not missed):
                    continue
            elif result_f == "Loss":
                if not (rr < -BE_THRESHOLD and not missed):
                    continue
            elif result_f == "BE":
                if not (-BE_THRESHOLD <= rr <= BE_THRESHOLD and not missed):
                    continue
            elif result_f == "Miss":
                if not missed:
                    continue
        result.append(row)

    return result


def filter_analysis(
    rows: List[Dict[str, Any]],
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Фильтрует список анализов в Python.

    Поддерживаемые ключи filters:
      date_from, date_to  — строки ISO
      asset, daily_bias, fact_bias, day_result, state — str
    """
    if not filters:
        return rows

    result = []
    date_from = filters.get("date_from")
    date_to = filters.get("date_to")
    simple_fields = {
        k: filters[k] for k in ("asset", "daily_bias", "fact_bias", "day_result", "state")
        if filters.get(k) is not None
    }

    for row in rows:
        if date_from and (row.get("date_local") or "") < date_from:
            continue
        if date_to and (row.get("date_local") or "") > date_to:
            continue
        skip = False
        for field, value in simple_fields.items():
            if row.get(field) != value:
                skip = True
                break
        if skip:
            continue
        result.append(row)

    return result


def filter_notes(
    rows: List[Dict[str, Any]],
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = "date_local",
    ascending: bool = False,
) -> List[Dict[str, Any]]:
    """Фильтрует список заметок в Python.

    Поддерживаемые ключи filters:
      date_from, date_to  — строки ISO
      query               — str (поиск в body, case-insensitive)
    """
    if not filters:
        result = list(rows)
    else:
        result = []
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")
        query = (filters.get("query") or "").lower()

        for row in rows:
            if date_from and (row.get("date_local") or "") < date_from:
                continue
            if date_to and (row.get("date_local") or "") > date_to:
                continue
            if query and query not in (row.get("body") or "").lower():
                continue
            result.append(row)

    # Сортировка
    if order_by in ("date_local", "time_local", "id"):
        result.sort(
            key=lambda r: (r.get("date_local") or "", r.get("time_local") or "", r.get("id") or 0),
            reverse=not ascending,
        )

    return result


def filter_setups(
    rows: List[Dict[str, Any]],
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = "name",
    ascending: bool = True,
) -> List[Dict[str, Any]]:
    """Фильтрует список сетапов в Python.

    Поддерживаемые ключи filters:
      query  — str (поиск в name и description, case-insensitive)
    """
    if not filters:
        result = list(rows)
    else:
        query = (filters.get("query") or "").lower()
        if not query:
            result = list(rows)
        else:
            result = [
                row for row in rows
                if query in (row.get("name") or "").lower()
                or query in (row.get("description") or "").lower()
            ]

    if order_by == "name":
        result.sort(
            key=lambda r: (r.get("name") or "").lower(),
            reverse=not ascending,
        )

    return result
