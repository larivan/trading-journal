import sqlite3
from datetime import date, timedelta
from utils.date_periods import compute_date_range
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from components.analysis_manager import render_analysis_manager
from components.entity_table import render_entity_table
from config import (
    ASSETS_VALUES,
    DAILY_BIAS_VALUES,
    DAY_RESULT_VALUES,
    ANALYSIS_STATE_VALUES,
    ANALYSIS_DIALOG_NAME,
    ANALYSIS_ID_STATE
)
from db import delete_analysis, list_analysis
from helpers import apply_page_config_from_file, format_local_date
from utils.session_state import (
    open_dialog,
    set_selected_entity,
)

# === ОСНОВНАЯ ИНИЦИАЛИЗАЦИЯ СТРАНИЦЫ АНАЛИЗОВ ===
apply_page_config_from_file(__file__)

TAB_DEFINITIONS: Dict[str, str] = {
    "today": "Today",
    "week": "Current week",
    "month": "Current month",
    "quarter": "Current quarter",
    "year": "Current year",
    "custom": "Custom",
}


def _open_new_analysis() -> None:
    st.session_state.pop(ANALYSIS_ID_STATE, None)
    open_dialog(ANALYSIS_DIALOG_NAME)


# === ВЕРХНЯЯ ПАНЕЛЬ С ВЫБОРОМ ПЕРИОДА ===
period_col, _, actions_col = st.columns(
    [0.5, 0.3, 0.2], vertical_alignment="bottom"
)
with period_col:
    period_key = "analysis_current_period_label"
    if not st.session_state.get(period_key):
        st.session_state[period_key] = list(TAB_DEFINITIONS.values())[0]
    selected_label = st.segmented_control(
        "Period",
        options=TAB_DEFINITIONS.values(),
        key=period_key,
        width="stretch",
    )

with actions_col:
    if st.button(
        "Create",
        type="primary",
        width="stretch",
    ):
        _open_new_analysis()

# === ФИЛЬТРЫ ПЕРИОДОВ И ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ ===
filters: Dict[str, Any] = {}
date_range: Optional[Tuple[date, date]] = None

label_to_key = {label: key for key, label in TAB_DEFINITIONS.items()}
selected_key = label_to_key.get(selected_label, "today")

if selected_key == "custom":
    with st.container():
        fc1, fc2, fc3, fc4, fc5, fc6 = st.columns(6)
        date_range = fc1.date_input(
            "Date Range",
            value=(
                date.today() - timedelta(days=7),
                date.today()
            ),
            format="DD.MM.YYYY",
        )
        asset_choice = fc2.selectbox(
            "Asset",
            ["All"] + ASSETS_VALUES
        )
        daily_bias_choice = fc3.selectbox(
            "Daily bias",
            ["All"] + DAILY_BIAS_VALUES
        )
        fact_bias_choice = fc4.selectbox(
            "Fact bias",
            ["All"] + DAILY_BIAS_VALUES
        )
        day_result_choice = fc5.selectbox(
            "Result",
            ["All"] + DAY_RESULT_VALUES
        )
        state_choice = fc6.selectbox(
            "Analysis Type",
            ["All"] + ANALYSIS_STATE_VALUES
        )

    if asset_choice != "All":
        filters["asset"] = asset_choice
    if daily_bias_choice != "All":
        filters["daily_bias"] = daily_bias_choice
    if fact_bias_choice != "All":
        filters["fact_bias"] = fact_bias_choice
    if day_result_choice != "All":
        filters["day_result"] = day_result_choice
    if state_choice != "All":
        filters["state"] = state_choice
else:
    date_range = compute_date_range(selected_key)

if date_range:
    if len(date_range) < 2:
        date_range = (date_range[0], date.today())
    filters["date_from"] = date_range[0].isoformat()
    filters["date_to"] = date_range[1].isoformat()

# === ЗАГРУЗКА ДАННЫХ ДЛЯ ОТОБРАЖЕНИЯ ===
rows = list_analysis(filters)


# --- Настройка колонок таблицы ---
analysis_columns: List[Dict[str, Any]] = [
    {
        "field": "date_local",
        "label": "Date",
        "compute": lambda row: row.get("date_local"),
        "format": format_local_date,
        "id": "date_local",
    },
    {"field": "asset", "label": "Asset", "id": "asset"},
    {"field": "daily_bias", "label": "Daily bias", "id": "daily_bias"},
    {"field": "fact_bias", "label": "Fact bias", "id": "fact_bias"},
    {"field": "day_result", "label": "Result", "id": "day_result"},
    {"field": "state", "label": "State", "id": "state"},
]


# === ОБРАБОТЧИКИ ДЕЙСТВИЙ ТАБЛИЦЫ ===
def _handle_open_analysis(row: Dict[str, Any]) -> None:
    analysis_id = row.get("id")
    if not analysis_id:
        return
    set_selected_entity("analysis", analysis_id)
    st.session_state[ANALYSIS_ID_STATE] = analysis_id
    open_dialog(ANALYSIS_DIALOG_NAME)


def _handle_delete_analyses(ids: List[Any]) -> None:
    if not ids:
        return
    st.session_state["_pending_delete_analysis_ids"] = ids
    st.rerun()


@st.dialog("Delete analyses")
def _confirm_delete_analyses(ids: List[Any]) -> None:
    n = len(ids)
    st.warning(f"Delete {n} {'analyses' if n > 1 else 'analysis'}? This cannot be undone.")
    col1, col2 = st.columns(2)
    if col1.button("Delete", type="primary", width="stretch"):
        for analysis_id in ids:
            try:
                delete_analysis(analysis_id)
            except (ValueError, sqlite3.Error) as exc:
                st.toast(f"Failed to delete analysis {analysis_id}: {exc}", icon="❌")
        st.session_state.pop("_pending_delete_analysis_ids", None)
        st.rerun()
    if col2.button("Cancel", width="stretch"):
        st.session_state.pop("_pending_delete_analysis_ids", None)
        st.rerun()


# --- Отрисовываем таблицу с подключенными обработчиками ---
table_key = f"analysis_table_{selected_key}"
render_entity_table(
    entity_name="analysis",
    key=table_key,
    rows=rows,
    columns=analysis_columns,
    empty_message="No analysis found for the selected period.",
    page_size=100,
    on_open=_handle_open_analysis,
    on_delete=_handle_delete_analyses,
)


# === ЛОГИКА УПРАВЛЕНИЯ МОДАЛЬНЫМИ ОКНАМИ ===
pending_delete_ids = st.session_state.get("_pending_delete_analysis_ids")
if pending_delete_ids:
    _confirm_delete_analyses(pending_delete_ids)

render_analysis_manager()
