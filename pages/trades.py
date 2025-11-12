from datetime import date, timedelta

import streamlit as st

from components.trade_filters import (
    TAB_DEFINITIONS,
    account_options,
    build_filters,
    tab_date_range,
)
from components.trades_table import render_trades_table
from components.trade_creator import render_trade_creator_dialog
from components.trade_manager import render_trade_manager_dialog
from components.trade_remover import render_trade_remove_dialog
from db import list_trades
from helpers import apply_page_config_from_file

# --- Базовая настройка страницы под Streamlit ---
apply_page_config_from_file(__file__)

# --- Загружаем список счетов и настраиваем state для форм ---
account_map = account_options()

# --- Первичные значения фильтров и диапазона дат ---
today = date.today()
st.session_state.setdefault("trades_active_filters", {})
st.session_state.setdefault(
    "trades_custom_range",
    (
        today - timedelta(days=7),
        today,
    ),
)

# --- Инициализируем рабочие флаги и выбранную сделку ---
st.session_state.setdefault("selected_trade_id", None)
st.session_state.setdefault("show_create_trade", False)
st.session_state.setdefault("show_edit_trade", False)
st.session_state.setdefault("show_delete_trade", False)


def set_dialog_flag(flag: str, value: bool) -> None:
    st.session_state[flag] = value


# --- Верхняя панель: слева фильтр периода, справа кнопки действий ---
period_col, actions_col = st.columns([0.7, 0.3], vertical_alignment="bottom")

with period_col:
    period_labels = [label for label, _ in TAB_DEFINITIONS]
    default_label = st.session_state.get(
        "trades_active_period", period_labels[0])
    selected_label = st.segmented_control(
        "Период",
        options=period_labels,
        default=default_label if default_label in period_labels else period_labels[0],
        key="trades_period_control",
    )

# Кнопки рендерим после таблицы, поэтому создаём placeholder заранее
actions_placeholder = actions_col.container()

# --- Фиксируем выбранный период и обнуляем выбор при переключении ---
label_to_key = {label: key for label, key in TAB_DEFINITIONS}
selected_tab_key = label_to_key.get(selected_label, TAB_DEFINITIONS[0][1])
previous_tab_key = st.session_state.get("trades_visible_tab")
if previous_tab_key != selected_tab_key:
    st.session_state["selected_trade_id"] = None
    set_dialog_flag("show_create_trade", False)
    set_dialog_flag("show_edit_trade", False)
    set_dialog_flag("show_delete_trade", False)
    table_state_key = f"trades_table_{selected_tab_key}"
    st.session_state.pop(table_state_key, None)
    st.session_state.pop(f"{table_state_key}_selection", None)
st.session_state["trades_visible_tab"] = selected_tab_key
st.session_state["trades_active_period"] = selected_label

# --- Собираем итоговый фильтр для таблицы ---
if selected_tab_key == "custom":
    filters, custom_range = build_filters(
        account_map,
        st.session_state.get("trades_active_filters"),
        st.session_state.get("trades_custom_range"),
    )
    st.session_state["trades_active_filters"] = filters
    st.session_state["trades_custom_range"] = custom_range
    tab_filters = filters.copy()
    date_from, date_to = custom_range
else:
    tab_filters = st.session_state.get("trades_active_filters", {}).copy()
    date_from, date_to = tab_date_range(selected_tab_key)
if date_from:
    tab_filters["date_from"] = date_from.isoformat()
if date_to:
    tab_filters["date_to"] = date_to.isoformat()

# --- Загружаем сделки и отслеживаем, изменилась ли выделенная строка ---
rows = list_trades(tab_filters)
selection_changed, selected_from_tab = render_trades_table(
    rows,
    selected_tab_key,
)
if selection_changed:
    if selected_from_tab is None:
        if not st.session_state.get("show_edit_trade"):
            st.session_state["selected_trade_id"] = None
            set_dialog_flag("show_create_trade", False)
            set_dialog_flag("show_edit_trade", False)
            set_dialog_flag("show_delete_trade", False)
    else:
        st.session_state["selected_trade_id"] = selected_from_tab
        set_dialog_flag("show_create_trade", False)
        set_dialog_flag("show_edit_trade", False)
        set_dialog_flag("show_delete_trade", False)

# --- Правый блок кнопок (создание / открытие / удаление) ---
open_disabled = st.session_state.get("selected_trade_id") is None
with actions_placeholder:
    create_col, open_col, delete_col = st.columns(
        3, vertical_alignment="bottom")
    with create_col:
        create_clicked = st.button(
            "Создать", type="primary", key="trades_btn_create", width="stretch")
    with open_col:
        open_clicked = st.button(
            "Открыть", disabled=open_disabled, key="trades_btn_open", width="stretch")
    with delete_col:
        delete_clicked = st.button(
            "Удалить", disabled=open_disabled, key="trades_btn_delete", width="stretch")

if create_clicked:
    set_dialog_flag("show_create_trade", True)
    set_dialog_flag("show_edit_trade", False)
    set_dialog_flag("show_delete_trade", False)
if open_clicked:
    set_dialog_flag("show_edit_trade", True)
    set_dialog_flag("show_create_trade", False)
    set_dialog_flag("show_delete_trade", False)
if delete_clicked:
    set_dialog_flag("show_delete_trade", True)
    set_dialog_flag("show_create_trade", False)
    set_dialog_flag("show_edit_trade", False)


def _close_create_dialog() -> None:
    set_dialog_flag("show_create_trade", False)
    st.rerun()


def _handle_trade_created(new_trade_id: int) -> None:
    st.session_state["selected_trade_id"] = new_trade_id
    set_dialog_flag("show_create_trade", False)
    set_dialog_flag("show_edit_trade", True)
    st.rerun()


def _close_edit_dialog() -> None:
    set_dialog_flag("show_edit_trade", False)
    st.rerun()


def _close_delete_dialog() -> None:
    set_dialog_flag("show_delete_trade", False)
    st.rerun()


def _handle_trade_deleted() -> None:
    st.session_state["selected_trade_id"] = None
    set_dialog_flag("show_delete_trade", False)
    st.rerun()


# --- В зависимости от флагов показываем нужные модалки ---
if st.session_state.get("show_create_trade"):
    render_trade_creator_dialog(
        on_created=_handle_trade_created,
        on_cancel=_close_create_dialog,
    )
if st.session_state.get("show_edit_trade"):
    render_trade_manager_dialog(
        trade_id=st.session_state.get("selected_trade_id"),
        on_close=_close_edit_dialog,
    )
if st.session_state.get("show_delete_trade"):
    render_trade_remove_dialog(
        trade_id=st.session_state.get("selected_trade_id"),
        on_deleted=_handle_trade_deleted,
        on_cancel=_close_delete_dialog,
    )
