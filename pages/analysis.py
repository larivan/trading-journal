from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from components.analysis_manager import render_analysis_manager
from components.entity_table import render_entity_table
from components.database_toolbar import render_database_toolbar
from components.entity_filters import (
    TAB_DEFINITIONS,
    ensure_custom_range,
)
from config import (
    ASSETS,
    DAILY_BIAS,
    DAY_RESULT_VALUES,
    ANALYSIS_STATE_VALUES
)
from db import delete_analysis, list_analysis
from helpers import apply_page_config_from_file, format_local_date
from utils.session_state import (
    apply_period_filters,
    close_entity_dialog,
    dialog_is_open,
    get_selected_entity,
    init_entity_state,
    open_entity_dialog,
    set_selected_entity,
)

# === ОСНОВНАЯ ИНИЦИАЛИЗАЦИЯ СТРАНИЦЫ АНАЛИЗОВ ===
apply_page_config_from_file(__file__)

today = date.today()
default_analysis_range = (today - timedelta(days=7), today)
init_entity_state(entity_name="analysis", default_range=default_analysis_range)


# === ОТРИСОВКА И ПРИМЕНЕНИЕ КАСТОМНЫХ ФИЛЬТРОВ ===
def _render_analysis_custom_filters(
    initial_range: Optional[Tuple[Optional[date], Optional[date]]],
) -> Tuple[Dict[str, Optional[str]], Tuple[Optional[date], Optional[date]]]:
    """Отрисовывает контент вкладки Custom для таблицы анализов."""
    default_from, default_to = ensure_custom_range(initial_range)

    asset_options = ["Все"] + ASSETS
    daily_bias_options = ["Все"] + DAILY_BIAS
    fact_bias_options = ["Все"] + DAILY_BIAS
    day_result_options = ["Все"] + DAY_RESULT_VALUES
    state_options = ["Все"] + ANALYSIS_STATE_VALUES

    with st.container():
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
        asset_choice = fc2.selectbox(
            "Инструмент",
            asset_options
        )
        daily_bias_choice = fc3.selectbox(
            "Daily bias",
            daily_bias_options
        )
        fact_bias_choice = fc4.selectbox(
            "Fact bias",
            fact_bias_options
        )
        day_result_choice = fc5.selectbox(
            "Результат",
            day_result_options
        )
        state_choice = fc6.selectbox(
            "Тип анализа",
            state_options
        )

    filters: Dict[str, Optional[str]] = {}
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

    return filters, (date_from, date_to)


# === ВЕРХНЯЯ ПАНЕЛЬ С ПЕРИОДОМ И СОЗДАНИЕМ АНАЛИЗОВ ===
render_database_toolbar(
    tab_definitions=TAB_DEFINITIONS,
    session_prefix="analysis",
)
tab_filters, date_from, date_to, selected_tab_key = apply_period_filters(
    entity_name="analysis",
    session_prefix="analysis",
    default_range=default_analysis_range,
    tab_definitions=TAB_DEFINITIONS,
    render_custom_filters=_render_analysis_custom_filters,
)

# === ЗАГРУЗКА ДАННЫХ ДЛЯ ОТОБРАЖЕНИЯ ===
rows = list_analysis(tab_filters)


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
    open_entity_dialog("analysis", "edit")


def _delete_analysis_and_refresh(analysis_id: Optional[int]) -> None:
    if not analysis_id:
        return
    try:
        delete_analysis(analysis_id)
        set_selected_entity("analysis", None)
        st.rerun()
    except Exception as exc:
        st.error(f"Не удалось удалить анализ: {exc}")


def _handle_delete_analyses(ids: List[Any]) -> None:
    if not ids:
        return
    _delete_analysis_and_refresh(ids[0])


# --- Отрисовываем таблицу с подключенными обработчиками ---
table_key = f"analysis_table_{selected_tab_key}"
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
def _close_edit_dialog() -> None:
    close_entity_dialog("analysis", "edit")
    st.rerun()


def _handle_analysis_created(new_id: int) -> None:
    set_selected_entity("analysis", new_id)
    open_entity_dialog("analysis", "edit")
    st.rerun()


def _close_create_dialog() -> None:
    close_entity_dialog("analysis", "create")
    st.rerun()


# === УСЛОВНЫЙ РЕНДЕР ДИАЛОГОВ СОГЛАСНО СОСТОЯНИЮ ===
if dialog_is_open("analysis", "create"):
    render_analysis_manager(
        analysis_id=None,
        on_created=_handle_analysis_created,
        on_close=_close_create_dialog,
    )
if dialog_is_open("analysis", "edit"):
    render_analysis_manager(
        analysis_id=get_selected_entity("analysis"),
        on_close=_close_edit_dialog,
    )
