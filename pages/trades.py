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
from config import ASSETS, TRADE_RESULT_VALUES, TRADE_SESSION_VALUES, TRADE_STATE_VALUES
from components.trades_table import render_trades_table
from components.trade_manager import (
    render_trade_creator,
    render_trade_editor,
    render_trade_remover,

)
from db import list_trades, list_accounts
from helpers import apply_page_config_from_file

# --- Базовая настройка страницы под Streamlit ---
apply_page_config_from_file(__file__)

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


def account_options() -> Dict[str, Optional[int]]:
    """Формирует удобный для отображения список счетов с их ID."""
    options: Dict[str, Optional[int]] = {"Все счета": None}
    for account in list_accounts():
        options[f"{account['name']} (#{account['id']})"] = account["id"]
    return options


# --- Загружаем список счетов и настраиваем state для форм ---
account_map = account_options()


def _render_trades_custom_filters(
    account_map: Dict[str, Optional[int]],
    initial_filters: Optional[Dict[str, Optional[str]]],
    initial_range: Optional[Tuple[Optional[date], Optional[date]]],
) -> Tuple[Dict[str, Optional[str]], Tuple[Optional[date], Optional[date]]]:
    """Отрисовывает контролы для таба Custom на странице сделок."""
    initial_filters = initial_filters or {}
    default_from, default_to = ensure_custom_range(initial_range)

    account_labels = list(account_map.keys())
    account_default_label = next(
        (label for label, val in account_map.items()
         if val == initial_filters.get("account_id")),
        account_labels[0],
    )

    asset_options = ["Все"] + ASSETS
    asset_default = initial_filters.get("asset", "Все")
    state_options = ["Все"] + TRADE_STATE_VALUES
    state_default = initial_filters.get("state", "Все")
    result_options = ["Все"] + TRADE_RESULT_VALUES
    result_default = initial_filters.get("result", "Все")
    session_options = ["Все"] + TRADE_SESSION_VALUES
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


def set_dialog_flag(flag: str, value: bool) -> None:
    st.session_state[flag] = value


# --- Верхняя панель: слева фильтр периода, справа кнопки действий ---
selected_label, selected_tab_key, tab_changed, actions_placeholder = render_database_toolbar(
    tab_definitions=TAB_DEFINITIONS,
    session_prefix="trades",
)

# --- Фиксируем выбранный период и обнуляем выбор при переключении ---
if tab_changed:
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
    filters, custom_range = _render_trades_custom_filters(
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
create_clicked, open_clicked, delete_clicked = render_action_buttons(
    actions_container=actions_placeholder,
    session_prefix="trades",
    open_disabled=open_disabled,
)

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
    render_trade_creator(
        on_created=_handle_trade_created,
        on_cancel=_close_create_dialog,
    )
if st.session_state.get("show_edit_trade"):
    render_trade_editor(
        trade_id=st.session_state.get("selected_trade_id"),
        on_close=_close_edit_dialog,
    )
if st.session_state.get("show_delete_trade"):
    render_trade_remover(
        trade_id=st.session_state.get("selected_trade_id"),
        on_deleted=_handle_trade_deleted,
        on_cancel=_close_delete_dialog,
    )
