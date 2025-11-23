from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from components.database_toolbar import render_database_toolbar
from components.entity_filters import (
    TAB_DEFINITIONS,
    ensure_custom_range,
)
from config import ASSETS, TRADE_RESULT_VALUES, TRADE_SESSION_VALUES, TRADE_STATE_VALUES
from components.entity_table import render_entity_table
from components.trade_manager import render_trade_manager
from db import delete_trade, list_accounts, list_trades
from helpers import apply_page_config_from_file, format_local_date, format_local_time, format_number
from utils.session_state import (
    apply_period_filters,
    close_entity_dialog,
    dialog_is_open,
    get_selected_entity,
    init_entity_state,
    open_entity_dialog,
    set_selected_entity,
    switch_to_edit_dialog,
)

# === БАЗОВАЯ ИНИЦИАЛИЗАЦИЯ СТРАНИЦЫ ===
# Настраиваем страницу и готовим исходные значения для фильтров и диапазонов.
apply_page_config_from_file(__file__)

today = date.today()
default_trades_range = (
    today - timedelta(days=7),
    today,
)
init_entity_state(entity_name="trade", default_range=default_trades_range)


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ФИЛЬТРОВ ===
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
    initial_range: Optional[Tuple[Optional[date], Optional[date]]],
) -> Tuple[Dict[str, Optional[str]], Tuple[Optional[date], Optional[date]]]:
    """Отрисовывает контролы для таба Custom на странице сделок."""
    default_from, default_to = ensure_custom_range(initial_range)

    account_labels = list(account_map.keys())

    asset_options = ["Все"] + ASSETS
    state_options = ["Все"] + TRADE_STATE_VALUES
    result_options = ["Все"] + TRADE_RESULT_VALUES
    session_options = ["Все"] + TRADE_SESSION_VALUES

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
        account_choice = fc2.selectbox(
            "Счёт",
            account_labels
        )
        asset_choice = fc3.selectbox(
            "Инструмент",
            asset_options
        )
        state_choice = fc4.selectbox(
            "Состояние",
            state_options
        )
        result_choice = fc5.selectbox(
            "Результат",
            result_options
        )
        session_choice = fc6.selectbox(
            "Сессия",
            session_options
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

    return filters, (date_from, date_to)


def _render_custom_trades_filters(
    initial_range: Optional[Tuple[Optional[date], Optional[date]]],
) -> Tuple[Dict[str, Optional[str]], Tuple[Optional[date], Optional[date]]]:
    return _render_trades_custom_filters(
        account_map,
        initial_range,
    )


# === ВЕРХНЯЯ ПАНЕЛЬ С ФИЛЬТРАМИ ПЕРИОДОВ ===
render_database_toolbar(
    tab_definitions=TAB_DEFINITIONS,
    session_prefix="trades",
)
tab_filters, date_from, date_to, selected_tab_key = apply_period_filters(
    entity_name="trade",
    session_prefix="trades",
    default_range=default_trades_range,
    tab_definitions=TAB_DEFINITIONS,
    render_custom_filters=_render_custom_trades_filters,
)

# === ЗАГРУЗКА ДАННЫХ И ОПРЕДЕЛЕНИЕ КОЛОНОК ===
rows = list_trades(tab_filters)


# --- Настройка отображаемых колонок таблицы ---
trade_table_columns: List[Dict[str, Any]] = [
    {
        "field": "date_local",
        "label": "Дата",
        "compute": lambda row: row.get("date_local"),
        "format": format_local_date,
        "id": "date_local",
    },
    {
        "field": "time_local",
        "label": "Время",
        "compute": lambda row: row.get("time_local"),
        "format": format_local_time,
        "id": "time_local",
    },
    {"field": "asset", "label": "Инструмент", "id": "asset"},
    {"field": "state", "label": "Состояние", "id": "state"},
    {"field": "result", "label": "Результат", "id": "result"},
    {
        "field": "net_pnl",
        "label": "PnL",
        "compute": lambda row: row.get("net_pnl"),
        "format": format_number,
        "id": "net_pnl",
    },
    {
        "field": "risk_reward",
        "label": "R:R",
        "compute": lambda row: row.get("risk_reward"),
        "format": format_number,
        "id": "risk_reward",
    },
    {"field": "session", "label": "Сессия", "id": "session"},
]


# === ДЕЙСТВИЯ ПРИ ВЗАИМОДЕЙСТВИИ С ТАБЛИЦЕЙ ===
def _handle_open_trade(row: Dict[str, Any]) -> None:
    trade_id = row.get("id")
    if not trade_id:
        return
    set_selected_entity("trade", trade_id)
    open_entity_dialog("trade", "edit")


def _delete_trade_and_refresh(trade_id: Optional[int]) -> None:
    if not trade_id:
        return
    try:
        delete_trade(trade_id)
        set_selected_entity("trade", None)
        st.rerun()
    except Exception as exc:
        st.error(f"Не удалось удалить сделку: {exc}")


def _handle_delete_trades(ids: List[Any]) -> None:
    if not ids:
        return
    first_id = ids[0]
    _delete_trade_and_refresh(first_id)


# --- Создаём таблицу с обработкой выделений и действий ---
table_key = f"trades_table_{selected_tab_key}"
render_entity_table(
    entity_name="trade",
    key=table_key,
    rows=rows,
    columns=trade_table_columns,
    empty_message="Нет сделок для выбранного периода.",
    page_size=100,
    on_open=_handle_open_trade,
    on_delete=_handle_delete_trades,
)


# === КОЛЛБЭКИ ДЛЯ МОДАЛОК СОЗДАНИЯ / РЕДАКТИРОВАНИЯ ===
def _handle_trade_created(new_trade_id: int) -> None:
    switch_to_edit_dialog("trade", new_trade_id)


def _close_edit_dialog() -> None:
    close_entity_dialog("trade", "edit")


def _close_create_dialog() -> None:
    close_entity_dialog("trade", "create")


# === ВЫЗОВ СООТВЕТСТВУЮЩИХ ДИАЛОГОВ В ЗАВИСИМОСТИ ОТ СОСТОЯНИЯ ===
if dialog_is_open("trade", "create"):
    render_trade_manager(
        trade_id=None,
        on_created=_handle_trade_created,
        on_close=_close_create_dialog,
    )
if dialog_is_open("trade", "edit"):
    render_trade_manager(
        trade_id=get_selected_entity("trade"),
        on_close=_close_edit_dialog,
    )
