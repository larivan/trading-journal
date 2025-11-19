from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from components.analysis_manager import (
    render_analysis_creator,
    render_analysis_editor,
    render_analysis_remover,
)
from components.entity_table import render_entity_table
from components.database_toolbar import render_database_toolbar
from components.entity_filters import (
    TAB_DEFINITIONS,
    ensure_custom_range,
    tab_date_range,
)
from config import (
    ASSETS,
    DAILY_BIAS,
    DAY_RESULT_VALUES,
    ANALYSIS_STATE_VALUES
)
from db import list_analysis
from helpers import apply_page_config_from_file
from utils.session_state import (
    clear_table_state,
    close_entity_dialog,
    consume_tab_change,
    dialog_is_open,
    get_custom_date_range,
    get_entity_filters,
    get_selected_entity,
    get_visible_tab,
    open_entity_dialog,
    reset_entity_state,
    set_custom_date_range,
    set_entity_filters,
    set_selected_entity,
)

# === ОСНОВНАЯ ИНИЦИАЛИЗАЦИЯ СТРАНИЦЫ АНАЛИЗОВ ===
apply_page_config_from_file(__file__)

today = date.today()
default_analysis_range = (today - timedelta(days=7), today)
st.session_state.setdefault("selected_analysis_id", None)
st.session_state.setdefault("show_create_analysis", False)
st.session_state.setdefault("show_edit_analysis", False)
st.session_state.setdefault("show_delete_analysis", False)


# === ОТРИСОВКА И ПРИМЕНЕНИЕ КАСТОМНЫХ ФИЛЬТРОВ ===
def _render_analysis_custom_filters(
    initial_filters: Optional[Dict[str, Optional[str]]],
    initial_range: Optional[Tuple[Optional[date], Optional[date]]],
) -> Tuple[Dict[str, Optional[str]], Tuple[Optional[date], Optional[date]]]:
    """Отрисовывает контент вкладки Custom для таблицы анализов."""
    initial_filters = initial_filters or {}
    default_from, default_to = ensure_custom_range(initial_range)

    asset_options = ["Все"] + ASSETS
    asset_default = initial_filters.get("asset", "Все")
    daily_bias_options = ["Все"] + DAILY_BIAS
    daily_bias_default = initial_filters.get("daily_bias", "Все")
    fact_bias_options = ["Все"] + DAILY_BIAS
    fact_bias_default = initial_filters.get("fact_bias", "Все")
    day_result_options = ["Все"] + DAY_RESULT_VALUES
    day_result_default = initial_filters.get("day_result", "Все")
    state_options = ["Все"] + ANALYSIS_STATE_VALUES
    state_default = initial_filters.get("state", "Все")

    with st.container():
        fc1, fc2, fc3, fc4, fc5, fc6 = st.columns(6)
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
        daily_bias_choice = fc3.selectbox(
            "Daily bias",
            daily_bias_options,
            index=daily_bias_options.index(daily_bias_default)
            if daily_bias_default in daily_bias_options
            else 0,
        )
        fact_bias_choice = fc4.selectbox(
            "Fact bias",
            fact_bias_options,
            index=fact_bias_options.index(fact_bias_default)
            if fact_bias_default in fact_bias_options
            else 0,
        )
        day_result_choice = fc5.selectbox(
            "Результат",
            day_result_options,
            index=day_result_options.index(day_result_default)
            if day_result_default in day_result_options
            else 0,
        )
        state_choice = fc6.selectbox(
            "Тип анализа",
            state_options,
            index=state_options.index(state_default)
            if state_default in state_options
            else 0,
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

    date_range = (
        date_from if isinstance(date_from, date) else default_from,
        date_to if isinstance(date_to, date) else default_to,
    )
    return filters, date_range


# === ВЕРХНЯЯ ПАНЕЛЬ С ПЕРИОДОМ И СОЗДАНИЕМ АНАЛИЗОВ ===
render_database_toolbar(
    tab_definitions=TAB_DEFINITIONS,
    session_prefix="analysis",
)
default_tab_key = TAB_DEFINITIONS[0][1]
selected_tab_key = get_visible_tab("analysis", default_tab_key)
tab_changed = consume_tab_change("analysis")

if tab_changed:
    reset_entity_state("analysis")
    clear_table_state("analysis", selected_tab_key)

# === ПРИМЕНЕНИЕ ФИЛЬТРОВ И ОПРЕДЕЛЕНИЕ ДИАПАЗОНА ===
if selected_tab_key == "custom":
    filters, custom_range = _render_analysis_custom_filters(
        get_entity_filters("analysis"),
        get_custom_date_range("analysis", default_analysis_range),
    )
    set_entity_filters("analysis", filters)
    set_custom_date_range("analysis", custom_range)
    tab_filters = dict(filters)
    date_from, date_to = custom_range
else:
    tab_filters = get_entity_filters("analysis")
    date_from, date_to = tab_date_range(selected_tab_key)
if date_from:
    tab_filters["date_from"] = date_from.isoformat()
if date_to:
    tab_filters["date_to"] = date_to.isoformat()

# === ЗАГРУЗКА ДАННЫХ ДЛЯ ОТОБРАЖЕНИЯ ===
rows = list_analysis(tab_filters)


def _format_date(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).strftime("%d.%m.%Y")
        except ValueError:
            return value
    return str(value)


# --- Настройка колонок таблицы ---
analysis_columns: List[Dict[str, Any]] = [
    {
        "field": "date_local",
        "label": "Дата",
        "compute": lambda row: row.get("date_local"),
        "format": _format_date,
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


def _handle_delete_analyses(ids: List[Any]) -> None:
    if not ids:
        return
    first_id = ids[0]
    set_selected_entity("analysis", first_id)
    open_entity_dialog("analysis", "delete")


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


def _close_delete_dialog() -> None:
    close_entity_dialog("analysis", "delete")
    st.rerun()


def _handle_analysis_deleted() -> None:
    set_selected_entity("analysis", None)
    close_entity_dialog("analysis", "delete")
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
    render_analysis_creator(
        on_created=_handle_analysis_created,
        on_cancel=_close_create_dialog,
    )
if dialog_is_open("analysis", "edit"):
    render_analysis_editor(
        analysis_id=get_selected_entity("analysis"),
        on_close=_close_edit_dialog,
    )
if dialog_is_open("analysis", "delete"):
    render_analysis_remover(
        analysis_id=get_selected_entity("analysis"),
        on_cancel=_close_delete_dialog,
        on_deleted=_handle_analysis_deleted,
    )
