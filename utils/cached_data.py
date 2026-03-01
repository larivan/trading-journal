"""Кешированные обёртки над db/ и вспомогательные функции Python-фильтрации.

Стратегия:
- prefetch_user_data() грузит ВСЕ данные пользователя ПАРАЛЛЕЛЬНО за один раз.
  Вместо 4-5 последовательных запросов × 300 мс ≈ 1.5 с получаем ~350 мс (max одного запроса).
- cached_*() — тонкие обёртки, берут данные из prefetch-кеша (без лишних DB-вызовов).
- st.cache_data.clear() сбрасывает всё после любой мутации.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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


# ---------------------------------------------------------------------------
# Параллельный prefetch — единственное место с реальными DB-вызовами
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def prefetch_user_data(user_id: int) -> Dict[str, List[Dict[str, Any]]]:
    """Загружает все коллекции пользователя параллельно.

    При user_id=None возвращает пустые списки без обращения к БД.
    Кешируется на уровне процесса — повторные вызовы с тем же user_id
    мгновенны.
    """
    if user_id is None:
        return {
            "trades": [], "analysis": [], "notes": [],
            "accounts": [], "accounts_archived": [], "setups": [],
        }

    tasks = {
        "trades":            (list_trades,    user_id),
        "analysis":          (list_analysis,  user_id),
        "notes":             (list_notes,     user_id),
        "accounts":          (list_accounts,  user_id, False),
        "accounts_archived": (list_accounts,  user_id, True),
        "setups":            (list_setups,    user_id),
    }

    t0 = time.perf_counter()
    result: Dict[str, List] = {}

    with ThreadPoolExecutor(max_workers=len(tasks)) as ex:
        futures = {ex.submit(fn, *args): key for key, (fn, *args) in tasks.items()}
        for future in as_completed(futures):
            key = futures[future]
            result[key] = future.result()

    ms = (time.perf_counter() - t0) * 1000
    sizes = " ".join(f"{k}={len(v)}" for k, v in result.items())
    _log.warning("[DB PARALLEL] user=%s  %s  total=%.0f ms", user_id, sizes, ms)
    return result


# ---------------------------------------------------------------------------
# Публичные обёртки — берут данные из prefetch-кеша
# ---------------------------------------------------------------------------

def cached_trades(user_id: int) -> List[Dict[str, Any]]:
    return prefetch_user_data(user_id)["trades"]


def cached_accounts(user_id: int, include_archived: bool = False) -> List[Dict[str, Any]]:
    key = "accounts_archived" if include_archived else "accounts"
    return prefetch_user_data(user_id)[key]


def cached_setups(user_id: int) -> List[Dict[str, Any]]:
    return prefetch_user_data(user_id)["setups"]


def cached_analysis(user_id: int) -> List[Dict[str, Any]]:
    return prefetch_user_data(user_id)["analysis"]


def cached_notes(user_id: int) -> List[Dict[str, Any]]:
    return prefetch_user_data(user_id)["notes"]


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
