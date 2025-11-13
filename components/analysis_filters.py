from datetime import date, timedelta
from typing import Dict, Optional, Tuple

import streamlit as st

from config import ASSETS, DAILY_BIAS

TAB_DEFINITIONS = [
    ("Today", "today"),
    ("Current week", "week"),
    ("Current month", "month"),
    ("Current quarter", "quarter"),
    ("Current year", "year"),
    ("Custom", "custom"),
]


def build_analysis_filters(
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

    asset_options = ["Все"] + ASSETS
    asset_default = initial_filters.get("asset", "Все")
    day_options = ["Все"] + DAILY_BIAS if DAILY_BIAS else ["Все"]
    day_default = initial_filters.get("day_result", "Все")

    fc1, fc2, fc3 = st.columns([0.5, 0.25, 0.25])
    date_from, date_to = fc1.date_input(
        "Диапазон дат",
        value=(default_from, default_to),
        format="DD.MM.YYYY",
    )
    asset_choice = fc2.selectbox(
        "Инструмент",
        asset_options,
        index=asset_options.index(asset_default)
        if asset_default in asset_options
        else 0,
    )
    day_choice = fc3.selectbox(
        "Day result",
        day_options,
        index=day_options.index(day_default)
        if day_default in day_options
        else 0,
    )

    filters: Dict[str, Optional[str]] = {}
    if asset_choice != "Все":
        filters["asset"] = asset_choice
    if day_choice != "Все":
        filters["day_result"] = day_choice

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
