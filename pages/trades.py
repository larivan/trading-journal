from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple
import streamlit as st
from components.entity_table import render_entity_table
from components.trade_manager import render_trade_manager
from db import delete_trade, list_accounts, list_trades
from helpers import (
    parse_date,
    to_option_format,
    apply_page_config_from_file,
    custom_selectbox,
)
from utils.session_state import (
    open_dialog,
)
from config import (
    ASSETS,
    TRADE_RESULT_VALUES,
    TRADE_SESSION_VALUES,
    TRADE_STATE_VALUES
)

# === БАЗОВАЯ ИНИЦИАЛИЗАЦИЯ СТРАНИЦЫ ===
# Настраиваем страницу и готовим исходные значения для фильтров и диапазонов.
apply_page_config_from_file(__file__)

TAB_DEFINITIONS: Dict[str, str] = {
    "today": "Today",
    "week": "Current week",
    "month": "Current month",
    "quarter": "Current quarter",
    "year": "Current year",
    "custom": "Custom",
}

ESTIMATION_VARS = {
    1: "Like",
    0: "Dislike",
}


# --- Загружаем список счетов и настраиваем state для форм ---
accounts = to_option_format(
    list_accounts(),
    formatter=lambda acc: f"{acc['name']}",
)

# === ВЕРХНЯЯ ПАНЕЛЬ С ФИЛЬТРАМИ ПЕРИОДОВ ===
period_col, _, actions_col = st.columns(
    [0.5, 0.3, 0.2], vertical_alignment="bottom"
)
with period_col:
    if not st.session_state.get("current_period_label", None):
        st.session_state["current_period_label"] = 'Today'
    selected_label = st.segmented_control(
        "Период",
        options=TAB_DEFINITIONS.values(),
        default=list(TAB_DEFINITIONS.values())[0],
        key="current_period_label",
        width="stretch",
    )

with actions_col:
    if st.button(
        "Create",
        type="primary",
        width="stretch",
    ):
        open_dialog("trade_manager")

# === ПРИМЕНЕНИЕ ПЕРИОДОВ И КАСТОМНЫХ ФИЛЬТРОВ ===
filter: Dict[str, Any] = {}
date_from: Optional[date] = None
date_to: Optional[date] = None
account_id: Optional[int] = None

label_to_key = {label: key for key, label in TAB_DEFINITIONS.items()}
selected_key = label_to_key.get(selected_label, "today")

if selected_key == "custom":
    with st.container():
        fc1, fc2, fc3, fc4, fc5, fc6, fc7 = st.columns(7)
        date_from, date_to = fc1.date_input(
            "Диапазон дат",
            value=(
                date.today() - timedelta(days=7),
                date.today()
            ),
            format="DD.MM.YYYY",
        )
        session = fc2.selectbox(
            "Session",
            TRADE_SESSION_VALUES,
            placeholder="All",
            index=None,
        )
        with fc3:
            account_id = custom_selectbox(
                "Account",
                accounts,
                placeholder="All",
            )
        asset = fc4.selectbox(
            "Asset",
            ASSETS,
            placeholder="All",
            index=None,
        )
        state = fc5.selectbox(
            "Status",
            TRADE_STATE_VALUES,
            placeholder="All",
            index=None,
        )
        result = fc6.selectbox(
            "Result",
            TRADE_RESULT_VALUES,
            placeholder="All",
            index=None,
        )
        estimation = fc7.selectbox(
            "Estimation",
            list(ESTIMATION_VARS.values()),
            placeholder="All",
            index=None,
        )

    if account_id:
        filter["account_id"] = account_id
    if state:
        filter["state"] = state
    if result:
        filter["result"] = result
    if asset:
        filter["asset"] = asset
    if session:
        filter["session"] = session
    if estimation:
        estimation_key = {val: key for key, val in ESTIMATION_VARS.items()}
        selected_estimation = estimation_key.get(estimation, None)
        filter["estimation"] = selected_estimation

else:
    today = date.today()
    if selected_key == "today":
        date_from, date_to = today, today
    elif selected_key == "week":
        date_from = today - timedelta(days=today.weekday())
        date_to = today
    elif selected_key == "month":
        date_from = today.replace(day=1)
        date_to = today
    elif selected_key == "quarter":
        quarter = (today.month - 1) // 3
        quarter_start_month = quarter * 3 + 1
        date_from = today.replace(month=quarter_start_month, day=1)
        date_to = today
    elif selected_key == "year":
        date_from = today.replace(month=1, day=1)
        date_to = today

if date_from:
    filter["date_from"] = date_from.isoformat()
if date_to:
    filter["date_to"] = date_to.isoformat()

# === ЗАГРУЗКА ДАННЫХ И ОПРЕДЕЛЕНИЕ КОЛОНОК ===
rows = list_trades(filter)


# --- Настройка отображаемых колонок таблицы ---
trade_table_columns: List[Dict[str, Any]] = [
    {
        "field": "date_local",
        "label": "Date",
        "compute": lambda row: row.get("date_local"),
        "format": parse_date,
        "id": "date_local",
    },
    {"field": "session", "label": "Session", "id": "session"},
    {"field": "asset", "label": "Asset", "id": "asset"},
    {"field": "state", "label": "Status", "id": "state"},
    {"field": "result", "label": "Result", "id": "result"},
    {"field": "net_pnl", "label": "PnL", "id": "net_pnl"},
    {"field": "risk_reward", "label": "R:R", "id": "risk_reward"},
]


# === ДЕЙСТВИЯ ПРИ ВЗАИМОДЕЙСТВИИ С ТАБЛИЦЕЙ ===
def _handle_open_trade(row: Dict[str, Any]) -> None:
    trade_id = row.get("id")
    if not trade_id:
        return
    st.session_state["tm_trade_id"] = trade_id
    open_dialog("trade_manager")


def _handle_delete_trades(ids: List[Any]) -> None:
    if not ids:
        return
    for id in ids:
        try:
            delete_trade(id)
        except Exception as exc:
            st.toast(f"Failed to delete trade with ID {id}: {exc}", icon="❌")
    st.rerun()


# --- Создаём таблицу с обработкой выделений и действий ---
table_key = f"trades_table_{selected_key}"
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

render_trade_manager()
