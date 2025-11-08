from datetime import date, timedelta
from typing import Dict, Optional

import pandas as pd
import streamlit as st

from components.trade_detail import trade_detail_fragment
from config import ASSETS, RESULT_VALUES, SESSION_VALUES, STATE_VALUES
from db import get_trade_by_id, list_accounts, list_trades
from helpers import apply_page_config_from_file

apply_page_config_from_file(__file__)


def _account_options() -> Dict[str, Optional[int]]:
    options: Dict[str, Optional[int]] = {"Все счета": None}
    for account in list_accounts():
        options[f"{account['name']} (#{account['id']})"] = account["id"]
    return options


def _build_filters(account_map: Dict[str, Optional[int]]) -> Dict[str, Optional[str]]:
    today = date.today()
    default_from = today - timedelta(days=7)
    with st.expander("Фильтры", expanded=True):
        fc1, fc2, fc3 = st.columns(3)
        account_choice = fc1.selectbox("Счёт", list(account_map.keys()))
        state_choice = fc2.selectbox("Состояние", ["Все"] + STATE_VALUES)
        result_choice = fc3.selectbox("Результат", ["Все"] + RESULT_VALUES)

        fc4, fc5 = st.columns(2)
        asset_choice = fc4.selectbox("Инструмент", ["Все"] + ASSETS)
        session_choice = fc5.selectbox("Сессия", ["Все"] + SESSION_VALUES)

        date_from, date_to = st.date_input(
            "Диапазон дат",
            value=(default_from, today),
            format="DD.MM.YYYY",
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
    if isinstance(date_from, date):
        filters["date_from"] = date_from.isoformat()
    if isinstance(date_to, date):
        filters["date_to"] = date_to.isoformat()
    return filters


@st.dialog("Просмотр сделки")
def _trade_dialog() -> None:
    trade_id = st.session_state.get("trade_dialog_id")
    if not trade_id:
        st.info("Сделка не выбрана.")
        return
    trade = get_trade_by_id(trade_id)
    if not trade:
        st.error("Сделка не найдена.")
        return
    trade_detail_fragment(trade)


account_map = _account_options()
active_filters = _build_filters(account_map)
rows = list_trades(active_filters)

if not rows:
    st.info("Нет сделок по заданным фильтрам.")
    st.stop()

df = pd.DataFrame(rows)
display_columns = [
    "id",
    "date_local",
    "time_local",
    "asset",
    "state",
    "result",
    "net_pnl",
    "risk_reward",
    "session",
]
table = df[display_columns].rename(columns={
    "id": "ID",
    "date_local": "Дата",
    "time_local": "Время",
    "asset": "Инструмент",
    "state": "Состояние",
    "result": "Результат",
    "net_pnl": "PnL",
    "risk_reward": "R:R",
    "session": "Сессия",
})

table_for_display = table.copy()
table_for_display["Дата"] = pd.to_datetime(
    table_for_display["Дата"], errors="coerce"
)
table_for_display["Время"] = pd.to_datetime(
    table_for_display["Время"], errors="coerce"
).dt.time
table_for_display["Открыть"] = table_for_display["ID"].apply(
    lambda tid: f"/trade-detail?trade_id={tid}"
)

trades = st.dataframe(
    table_for_display,
    key="trades_table",
    width="stretch",
    hide_index=True,
    on_select="rerun",
    selection_mode=["multi-row", "multi-column", "multi-cell"],
    column_config={
        "Дата": st.column_config.DateColumn("Дата", format="DD.MM.YYYY"),
        "Время": st.column_config.TimeColumn("Время"),
        "PnL": st.column_config.NumberColumn("PnL", format="%.2f"),
        "R:R": st.column_config.NumberColumn("R:R", format="%.2f"),
        "Открыть": st.column_config.LinkColumn(
            "Открыть",
            help="Перейти на страницу сделки",
            display_text="Страница",
        ),
    },
)

trades.selection

selected_trade_id: Optional[int] = None
table_state = st.session_state.get("trades_table", {})
selected_rows = table_state.get("selection", {}).get(
    "rows") if table_state else None
if selected_rows:
    selected_idx = selected_rows[-1]
    selected_trade_id = int(table.iloc[selected_idx]["ID"])

if selected_trade_id:
    st.session_state["trade_dialog_id"] = selected_trade_id
    _trade_dialog()
else:
    st.info("Кликните строку в таблице, чтобы открыть сделку в диалоге.")
