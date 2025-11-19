from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from components.database_toolbar import render_database_toolbar
from components.entity_filters import (
    TAB_DEFINITIONS,
    ensure_custom_range,
    tab_date_range,
)
from config import ASSETS, TRADE_RESULT_VALUES, TRADE_SESSION_VALUES, TRADE_STATE_VALUES
from components.entity_table import render_entity_table
from components.trade_manager import render_trade_manager
from db import delete_trade, list_accounts, list_trades
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

# === БАЗОВАЯ ИНИЦИАЛИЗАЦИЯ СТРАНИЦЫ ===
# Настраиваем страницу и готовим исходные значения для фильтров и диапазонов.
apply_page_config_from_file(__file__)

today = date.today()
default_trades_range = (
    today - timedelta(days=7),
    today,
)
st.session_state.setdefault("selected_trade_id", None)
st.session_state.setdefault("show_create_trade", False)
st.session_state.setdefault("show_edit_trade", False)


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


# === ВЕРХНЯЯ ПАНЕЛЬ С ФИЛЬТРАМИ ПЕРИОДОВ ===
render_database_toolbar(
    tab_definitions=TAB_DEFINITIONS,
    session_prefix="trades",
)
default_tab_key = TAB_DEFINITIONS[0][1]
selected_tab_key = get_visible_tab("trades", default_tab_key)
tab_changed = consume_tab_change("trades")

# --- Переключение табов требует очистки состояний таблицы и диалогов ---
if tab_changed:
    reset_entity_state("trade")
    clear_table_state("trades", selected_tab_key)

# === СБОР ФИЛЬТРОВ ДЛЯ ЗАПРОСА ДАННЫХ ===
if selected_tab_key == "custom":
    filters, custom_range = _render_trades_custom_filters(
        account_map,
        get_entity_filters("trades"),
        get_custom_date_range("trades", default_trades_range),
    )
    set_entity_filters("trades", filters)
    set_custom_date_range("trades", custom_range)
    tab_filters = dict(filters)
    date_from, date_to = custom_range
else:
    tab_filters = get_entity_filters("trades")
    date_from, date_to = tab_date_range(selected_tab_key)
if date_from:
    tab_filters["date_from"] = date_from.isoformat()
if date_to:
    tab_filters["date_to"] = date_to.isoformat()

# === ЗАГРУЗКА ДАННЫХ И ОПРЕДЕЛЕНИЕ КОЛОНОК ===
rows = list_trades(tab_filters)


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


def _format_time(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).strftime("%H:%M")
        except ValueError:
            return value[:5]
    return str(value)


def _format_number(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


# --- Настройка отображаемых колонок таблицы ---
trade_table_columns: List[Dict[str, Any]] = [
    {
        "field": "date_local",
        "label": "Дата",
        "compute": lambda row: row.get("date_local"),
        "format": _format_date,
        "id": "date_local",
    },
    {
        "field": "time_local",
        "label": "Время",
        "compute": lambda row: row.get("time_local"),
        "format": _format_time,
        "id": "time_local",
    },
    {"field": "asset", "label": "Инструмент", "id": "asset"},
    {"field": "state", "label": "Состояние", "id": "state"},
    {"field": "result", "label": "Результат", "id": "result"},
    {
        "field": "net_pnl",
        "label": "PnL",
        "compute": lambda row: row.get("net_pnl"),
        "format": _format_number,
        "id": "net_pnl",
    },
    {
        "field": "risk_reward",
        "label": "R:R",
        "compute": lambda row: row.get("risk_reward"),
        "format": _format_number,
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
    set_selected_entity("trade", new_trade_id)
    open_entity_dialog("trade", "edit")
    st.rerun()


def _close_edit_dialog() -> None:
    close_entity_dialog("trade", "edit")
    st.rerun()


def _close_create_dialog() -> None:
    close_entity_dialog("trade", "create")
    st.rerun()


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
