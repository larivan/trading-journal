from datetime import date, timedelta
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


def _tab_date_range(tab_key: str) -> Tuple[Optional[date], Optional[date]]:
    today = date.today()
    if tab_key == "today":
        return today, today
    if tab_key == "week":
        start = today - timedelta(days=today.weekday())
        return start, today
    if tab_key == "month":
        start = today.replace(day=1)
        return start, today
    if tab_key == "quarter":
        quarter = (today.month - 1) // 3
        month_start = quarter * 3 + 1
        start = today.replace(month=month_start, day=1)
        return start, today
    if tab_key == "year":
        start = today.replace(month=1, day=1)
        return start, today
    return None, None


# === ВЕРХНЯЯ ПАНЕЛЬ С ВЫБОРОМ ПЕРИОДА ===
period_col, _, actions_col = st.columns(
    [0.5, 0.3, 0.2], vertical_alignment="bottom"
)
with period_col:
    period_key = "analysis_current_period_label"
    if not st.session_state.get(period_key):
        st.session_state[period_key] = list(TAB_DEFINITIONS.values())[0]
    selected_label = st.segmented_control(
        "Период",
        options=TAB_DEFINITIONS.values(),
        default=list(TAB_DEFINITIONS.values())[0],
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
date_from: Optional[date] = None
date_to: Optional[date] = None

label_to_key = {label: key for key, label in TAB_DEFINITIONS.items()}
selected_key = label_to_key.get(selected_label, "today")

if selected_key == "custom":
    with st.container():
        default_from = date.today() - timedelta(days=7)
        default_to = date.today()
        fc1, fc2, fc3, fc4, fc5, fc6 = st.columns(6)
        raw_date_range = fc1.date_input(
            "Диапазон дат",
            value=(default_from, default_to),
            format="DD.MM.YYYY",
        )
        if isinstance(raw_date_range, (list, tuple)):
            range_values = list(raw_date_range)
            while len(range_values) < 2:
                range_values.append(default_to)
            raw_from, raw_to = range_values[:2]
        else:
            raw_from, raw_to = raw_date_range, default_to
        date_from = raw_from if isinstance(raw_from, date) else default_from
        date_to = raw_to if isinstance(raw_to, date) else default_to
        asset_choice = fc2.selectbox("Инструмент", ["Все"] + ASSETS_VALUES)
        daily_bias_choice = fc3.selectbox(
            "Daily bias", ["Все"] + DAILY_BIAS_VALUES)
        fact_bias_choice = fc4.selectbox(
            "Fact bias", ["Все"] + DAILY_BIAS_VALUES)
        day_result_choice = fc5.selectbox(
            "Результат", ["Все"] + DAY_RESULT_VALUES
        )
        state_choice = fc6.selectbox(
            "Тип анализа", ["Все"] + ANALYSIS_STATE_VALUES
        )

    if asset_choice != "Все":
        filters["asset"] = asset_choice
    if daily_bias_choice != "Все":
        filters["daily_bias"] = daily_bias_choice
    if fact_bias_choice != "Все":
        filters["fact_bias"] = fact_bias_choice
    if day_result_choice != "Все":
        filters["day_result"] = day_result_choice
    if state_choice != "Все":
        filters["state"] = state_choice
else:
    date_from, date_to = _tab_date_range(selected_key)

if date_from:
    filters["date_from"] = date_from.isoformat()
if date_to:
    filters["date_to"] = date_to.isoformat()

# === ЗАГРУЗКА ДАННЫХ ДЛЯ ОТОБРАЖЕНИЯ ===
rows = list_analysis(filters)


# --- Настройка колонок таблицы ---
analysis_columns: List[Dict[str, Any]] = [
    {
        "field": "date_local",
        "label": "Дата",
        "compute": lambda row: row.get("date_local"),
        "format": format_local_date,
        "id": "date_local",
    },
    {"field": "asset", "label": "Инструмент", "id": "asset"},
    {"field": "daily_bias", "label": "Daily bias", "id": "daily_bias"},
    {"field": "fact_bias", "label": "Fact bias", "id": "fact_bias"},
    {"field": "day_result", "label": "Result", "id": "day_result"},
    {"field": "state", "label": "Тип анализа", "id": "state"},
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
    for id in ids:
        try:
            delete_analysis(id)
        except Exception as exc:
            st.toast(f"Failed to delete trade with ID {id}: {exc}", icon="❌")
    st.rerun()


# --- Отрисовываем таблицу с подключенными обработчиками ---
table_key = f"analysis_table_{selected_key}"
render_entity_table(
    entity_name="analysis",
    key=table_key,
    rows=rows,
    columns=analysis_columns,
    empty_message="Нет анализов за выбранный период.",
    page_size=100,
    on_open=_handle_open_analysis,
    on_delete=_handle_delete_analyses,
)


# === ЛОГИКА УПРАВЛЕНИЯ МОДАЛЬНЫМИ ОКНАМИ ===
render_analysis_manager()
