from datetime import date, timedelta
from typing import Dict, Optional, Tuple

import streamlit as st

from config import ASSETS, RESULT_VALUES, SESSION_VALUES, STATE_VALUES
from db import list_accounts

TAB_DEFINITIONS = [
    ("Today", "today"),
    ("Current week", "week"),
    ("Current month", "month"),
    ("Current quarter", "quarter"),
    ("Current year", "year"),
    ("Custom", "custom"),
]


def account_options() -> Dict[str, Optional[int]]:
    options: Dict[str, Optional[int]] = {"Все счета": None}
    for account in list_accounts():
        options[f"{account['name']} (#{account['id']})"] = account["id"]
    return options


def build_filters(
    account_map: Dict[str, Optional[int]],
    initial_filters: Optional[Dict[str, Optional[str]]] = None,
    initial_range: Optional[Tuple[Optional[date], Optional[date]]] = None,
) -> Tuple[Dict[str, Optional[str]], Tuple[Optional[date], Optional[date]]]:
    initial_filters = initial_filters or {}
    today = date.today()
    default_from, default_to = initial_range or (
        today - timedelta(days=7),
        today,
    )
    if not isinstance(default_from, date):
        default_from = today - timedelta(days=7)
    if not isinstance(default_to, date):
        default_to = today

    account_labels = list(account_map.keys())
    account_default_label = next(
        (label for label, val in account_map.items()
         if val == initial_filters.get("account_id")),
        account_labels[0],
    )

    asset_options = ["Все"] + ASSETS
    asset_default = initial_filters.get("asset", "Все")
    state_options = ["Все"] + STATE_VALUES
    state_default = initial_filters.get("state", "Все")
    result_options = ["Все"] + RESULT_VALUES
    result_default = initial_filters.get("result", "Все")
    session_options = ["Все"] + SESSION_VALUES
    session_default = initial_filters.get("session", "Все")

    with st.container():
        fc1, fc2, fc3, fc4, fc5, fc6 = st.columns(6)
        date_from, date_to = fc1.date_input(
            "Диапазон дат",
            value=(default_from, default_to),
            format="DD.MM.YYYY",
        )
        account_choice = fc2.selectbox(
            "Счёт",
            account_labels,
            index=account_labels.index(account_default_label),
        )
        asset_choice = fc3.selectbox(
            "Инструмент",
            asset_options,
            index=asset_options.index(asset_default)
            if asset_default in asset_options else 0,
        )
        state_choice = fc4.selectbox(
            "Состояние",
            state_options,
            index=state_options.index(state_default)
            if state_default in state_options else 0,
        )
        result_choice = fc5.selectbox(
            "Результат",
            result_options,
            index=result_options.index(result_default)
            if result_default in result_options else 0,
        )
        session_choice = fc6.selectbox(
            "Сессия",
            session_options,
            index=session_options.index(session_default)
            if session_default in session_options else 0,
        )

    filters: Dict[str, Optional[str]] = {}
    account_id = account_map.get(account_choice)
    if account_id:
        filters["account_id"] = account_id
    if state_choice != "Все":
        filters["state"] = state_choice
    if result_choice != "Все":
        filters["result"] = result_choice
    if asset_choice != "Все":
        filters["asset"] = asset_choice
    if session_choice != "Все":
        filters["session"] = session_choice

    date_range = (
        date_from if isinstance(date_from, date) else default_from,
        date_to if isinstance(date_to, date) else default_to,
    )
    return filters, date_range


def tab_date_range(tab_key: str) -> Tuple[Optional[date], Optional[date]]:
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
