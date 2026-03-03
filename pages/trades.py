import sqlite3
from datetime import date, datetime, timedelta
from utils.date_periods import compute_date_range
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import streamlit as st
from db import create_trade, delete_trade, transaction
from utils.cached_data import cached_accounts, cached_trades, filter_trades, page_mark
from helpers import (
    parse_date,
    to_option_format,
    custom_selectbox,
    calculate_trade_result,
)
from utils.auth import get_current_user_id, get_setting
from utils.trade_sessions import detect_trade_session
from config import (
    ASSETS_VALUES,
    LOCAL_TZ,
    TRADE_RESULT_VALUES,
    TRADE_SESSION_VALUES,
    TRADE_STATE_VALUES,
)

# === БАЗОВАЯ ИНИЦИАЛИЗАЦИЯ СТРАНИЦЫ ===
st.set_page_config(page_title="Trades Database",
                   page_icon=":material/view_list:", layout="wide")
st.title(":material/view_list: Trades Database")
page_mark("trades", "start")

user_id = get_current_user_id()

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


# --- Загружаем список счетов и ассеты ---
account_rows_all = cached_accounts(user_id)
assets_list = get_setting("assets", ASSETS_VALUES)
accounts = to_option_format(
    account_rows_all, formatter=lambda acc: f"{acc['name']}")

# === ВЕРХНЯЯ ПАНЕЛЬ С ФИЛЬТРАМИ ПЕРИОДОВ ===
period_col, _ = st.columns([0.7, 0.3], vertical_alignment="bottom")
with period_col:
    period_key = "trade_current_period_label"
    if not st.session_state.get(period_key):
        st.session_state[period_key] = "Current month"
    selected_label = st.segmented_control(
        "Period",
        options=TAB_DEFINITIONS.values(),
        key=period_key,
        width="stretch",
    )

# === ПРИМЕНЕНИЕ ПЕРИОДОВ И КАСТОМНЫХ ФИЛЬТРОВ ===
filter: Dict[str, Any] = {}
date_range: Optional[Tuple[date, date]] = None
account_id: Optional[int] = None
asset: Optional[str] = None

label_to_key = {label: key for key, label in TAB_DEFINITIONS.items()}
selected_key = label_to_key.get(selected_label, "today")

if selected_key == "custom":
    with st.container():
        fc1, fc2, fc3, fc4, fc5, fc6, fc7 = st.columns(7)
        date_range = fc1.date_input(
            "Date Range",
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
            assets_list,
            placeholder="All",
            index=None,
        )
        state = fc5.selectbox(
            "State",
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
    local_tz = get_setting("local_tz", LOCAL_TZ)
    date_range = compute_date_range(selected_key, tz_name=local_tz)

if date_range:
    if len(date_range) < 2:
        date_range = (date_range[0], date.today())
    filter["date_from"] = date_range[0].isoformat()
    filter["date_to"] = date_range[1].isoformat()

# === ЗАГРУЗКА ДАННЫХ ===
rows = filter_trades(cached_trades(user_id), filter)
page_mark("trades", "data_loaded")


# === ТАБЛИЦА ===
selected_rows: List[int] = []
if not rows:
    st.info("No trades for the selected period.")
else:
    df = pd.DataFrame(rows)
    df["result"] = df.apply(
        lambda r: calculate_trade_result(
            r.get("risk_reward"), r.get("is_missed")),
        axis=1,
    )
    df["_link"] = "/trade_editor?id=" + df["id"].astype(str)

    display_cols = ["_link", "date_local", "session",
                    "asset", "state", "result", "net_pnl", "risk_reward"]
    for col in display_cols:
        if col not in df.columns:
            df[col] = None

    event = st.dataframe(
        df[display_cols],
        column_config={
            "date_local": st.column_config.TextColumn("Date"),
            "session": st.column_config.TextColumn("Session"),
            "asset": st.column_config.TextColumn("Asset"),
            "state": st.column_config.TextColumn("State"),
            "result": st.column_config.TextColumn("Result"),
            "net_pnl": st.column_config.NumberColumn("PnL"),
            "risk_reward": st.column_config.NumberColumn("R:R"),
            "_link": st.column_config.LinkColumn("Open", display_text="Open"),
        },
        selection_mode="multi-row",
        on_select="rerun",
        use_container_width=True,
        hide_index=True,
        key=f"trades_dataframe_{selected_key}",
    )

    selected_rows = event.selection.rows

btn_create, btn_delete, _ = st.columns([0.12, 0.15, 0.73])
with btn_create.popover("Create", type="primary", width="stretch"):
    if not account_rows_all:
        st.error("Create an account first.")
    else:
        valid_ids = {acc["id"] for acc in account_rows_all}
        default_acc = (
            account_id
            or (get_setting("default_account_id") if get_setting("default_account_id") in valid_ids else None)
            or account_rows_all[0]["id"]
        )
        default_ast = (
            (asset if asset in assets_list else None)
            or (get_setting("default_asset") if get_setting("default_asset") in assets_list else None)
            or (assets_list[0] if assets_list else "EUR/USD")
        )
        pop_account = custom_selectbox(
            "Account", accounts, value=default_acc, key="_create_pop_account"
        )
        pop_asset = st.selectbox(
            "Asset", assets_list,
            index=assets_list.index(
                default_ast) if default_ast in assets_list else 0,
            key="_create_pop_asset",
        )
        if st.button("Go", type="primary", width=250, key="_create_pop_go"):
            local_tz = get_setting("local_tz", LOCAL_TZ)
            today = date.today()
            now = datetime.now()
            with transaction() as conn:
                new_id = create_trade(user_id, {
                    "date_local": today.isoformat(),
                    "time_local": now.strftime("%H:%M:%S"),
                    "account_id": pop_account,
                    "asset": pop_asset,
                    "session": detect_trade_session(today, now.time(), local_tz_label=local_tz),
                    "state": "Open",
                    "local_tz": local_tz,
                    "is_missed": 0,
                }, conn=conn)
            st.cache_data.clear()
            st.session_state["_new_trade_id"] = new_id
            st.switch_page("pages/trade_editor.py")
if selected_rows:
    selected_ids = [rows[i]["id"] for i in selected_rows]
    if btn_delete.button(f"Delete ({len(selected_ids)})", type="secondary", width="stretch"):
        st.session_state["_pending_delete_trade_ids"] = selected_ids
        st.rerun()


@st.dialog("Delete trades")
def _confirm_delete_trades(ids: List[Any]) -> None:
    n = len(ids)
    st.warning(
        f"Delete {n} trade{'s' if n > 1 else ''}? This cannot be undone.")
    col1, col2 = st.columns(2)
    if col1.button("Delete", type="primary", width="stretch"):
        from db import transaction
        try:
            with transaction() as conn:
                for trade_id in ids:
                    try:
                        delete_trade(trade_id, user_id, conn=conn)
                    except (ValueError, sqlite3.Error) as exc:
                        st.toast(
                            f"Failed to delete trade {trade_id}: {exc}", icon="❌")
        except Exception as exc:
            st.toast(f"Delete failed: {exc}", icon="❌")
        st.session_state.pop("_pending_delete_trade_ids", None)
        st.cache_data.clear()
        st.rerun()
    if col2.button("Cancel", width="stretch"):
        st.session_state.pop("_pending_delete_trade_ids", None)
        st.rerun()


pending_delete_ids = st.session_state.get("_pending_delete_trade_ids")
if pending_delete_ids:
    _confirm_delete_trades(pending_delete_ids)

page_mark("trades", "done")
