from datetime import date, timedelta
from typing import Dict, Optional

import pandas as pd
import streamlit as st

from config import ASSETS, RESULT_VALUES, SESSION_VALUES, STATE_VALUES
from db import list_accounts, list_trades
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
    with st.container():
        fc1, fc2, fc3, fc4, fc5, fc6 = st.columns(6)
        date_from, date_to = fc1.date_input(
            "Диапазон дат",
            value=(default_from, today),
            format="DD.MM.YYYY",
        )
        account_choice = fc2.selectbox("Счёт", list(account_map.keys()))
        asset_choice = fc3.selectbox("Инструмент", ["Все"] + ASSETS)
        state_choice = fc4.selectbox("Состояние", ["Все"] + STATE_VALUES)
        result_choice = fc5.selectbox("Результат", ["Все"] + RESULT_VALUES)
        session_choice = fc6.selectbox("Сессия", ["Все"] + SESSION_VALUES)

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


account_map = _account_options()
active_filters = _build_filters(account_map)
rows = list_trades(active_filters)

if not rows:
    st.info("Нет сделок по заданным фильтрам.")
    st.stop()

df = pd.DataFrame(rows)
display_columns = [
    "date_local",
    "asset",
    "state",
    "result",
    "net_pnl",
    "risk_reward",
    "session",
]
table = df[display_columns].rename(columns={
    "date_local": "Дата",
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
table_for_display["Открыть"] = df["id"].apply(lambda tid: f"/trade-detail?trade_id={tid}")

st.dataframe(
    table_for_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Дата": st.column_config.DateColumn("Дата", format="DD.MM.YYYY"),
        "PnL": st.column_config.NumberColumn("PnL", format="%.2f"),
        "R:R": st.column_config.NumberColumn("R:R", format="%.2f"),
        "Открыть": st.column_config.LinkColumn(
            "Открыть",
            help="Перейти на страницу сделки",
            display_text="Страница",
        ),
    },
)