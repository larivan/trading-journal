from datetime import date, timedelta
from typing import Dict, Optional, Tuple

import streamlit as st

from components.database_toolbar import (
    render_action_buttons,
    render_database_toolbar,
)
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

# --- Базовая настройка страницы под Streamlit ---
apply_page_config_from_file(__file__)

today = date.today()
st.session_state.setdefault("analysis_active_filters", {})
st.session_state.setdefault(
    "analysis_custom_range",
    (today - timedelta(days=7), today),
)
st.session_state.setdefault("selected_analysis_id", None)


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


selected_label, selected_tab_key, tab_changed, actions_placeholder = render_database_toolbar(
    tab_definitions=TAB_DEFINITIONS,
    session_prefix="analysis",
)

if tab_changed:
    st.session_state["selected_analysis_id"] = None
    st.session_state.pop(f"analysis_table_{selected_tab_key}", None)
    st.session_state.pop(f"analysis_table_{selected_tab_key}_selection", None)
st.session_state["analysis_visible_tab"] = selected_tab_key
st.session_state["analysis_active_period"] = selected_label

if selected_tab_key == "custom":
    filters, custom_range = _render_analysis_custom_filters(
        st.session_state.get("analysis_active_filters"),
        st.session_state.get("analysis_custom_range"),
    )
    st.session_state["analysis_active_filters"] = filters
    st.session_state["analysis_custom_range"] = custom_range
    tab_filters = filters.copy()
    date_from, date_to = custom_range
else:
    tab_filters = st.session_state.get("analysis_active_filters", {}).copy()
    date_from, date_to = tab_date_range(selected_tab_key)
if date_from:
    tab_filters["date_from"] = date_from.isoformat()
if date_to:
    tab_filters["date_to"] = date_to.isoformat()

rows = list_analysis(tab_filters)

if rows:
    st.dataframe(rows, use_container_width=True, hide_index=True)
    selector_options = ["— Не выбран —"] + [
        f"{row['date_local']} · {row.get('asset') or '—'} (#{row['id']})"
        for row in rows
    ]
    selected_id = st.session_state.get("selected_analysis_id")
    default_option = 0
    if selected_id:
        for idx, row in enumerate(rows, start=1):
            if row["id"] == selected_id:
                default_option = idx
                break
    choice = st.radio(
        "Выберите анализ",
        selector_options,
        index=default_option,
        key="analysis_row_selector",
    )
    if choice == selector_options[0]:
        st.session_state["selected_analysis_id"] = None
    else:
        choice_index = selector_options.index(choice) - 1
        st.session_state["selected_analysis_id"] = rows[choice_index]["id"]
else:
    st.info("Нет анализов за выбранный период.")
    st.session_state["selected_analysis_id"] = None

open_disabled = st.session_state.get("selected_analysis_id") is None
create_clicked, open_clicked, delete_clicked = render_action_buttons(
    actions_container=actions_placeholder,
    session_prefix="analysis",
    open_disabled=open_disabled,
)

if create_clicked:
    st.info("Создание анализа пока недоступно.")
if open_clicked:
    st.info("Перейти к редактированию анализа пока нельзя.")
if delete_clicked:
    st.info("Удаление анализа будет добавлено позже.")
