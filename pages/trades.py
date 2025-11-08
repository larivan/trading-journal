from datetime import date, timedelta

import streamlit as st

from components.trade_dialogs import (
    create_trade_dialog,
    delete_trade_dialog,
    edit_trade_dialog,
    set_dialog_flag,
)
from components.trade_filters import (
    TAB_DEFINITIONS,
    account_options,
    build_filters,
    tab_date_range,
)
from components.trades_table import render_trades_table
from db import list_trades
from helpers import apply_page_config_from_file

apply_page_config_from_file(__file__)

account_map = account_options()
st.session_state["account_options_for_forms"] = account_map

today = date.today()
st.session_state.setdefault("trades_active_filters", {})
st.session_state.setdefault(
    "trades_custom_range",
    (
        today - timedelta(days=7),
        today,
    ),
)

st.session_state.setdefault("selected_trade_id", None)
st.session_state.setdefault("show_create_trade", False)
st.session_state.setdefault("show_edit_trade", False)
st.session_state.setdefault("show_delete_trade", False)

buttons_container = st.container()
tabs_container = st.container()

with tabs_container:
    tabs = st.tabs([label for label, _ in TAB_DEFINITIONS])
    for tab, (label, tab_key) in zip(tabs, TAB_DEFINITIONS):
        with tab:
            if tab_key == "custom":
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
                date_from, date_to = tab_date_range(tab_key)
            if date_from:
                tab_filters["date_from"] = date_from.isoformat()
            if date_to:
                tab_filters["date_to"] = date_to.isoformat()
            rows = list_trades(tab_filters)
            selection_changed, selected_from_tab = render_trades_table(
                rows,
                tab_key,
            )
            if selection_changed:
                st.session_state["selected_trade_id"] = selected_from_tab
                set_dialog_flag("show_create_trade", False)
                set_dialog_flag("show_edit_trade", False)
                set_dialog_flag("show_delete_trade", False)

with buttons_container:
    action_cols = st.columns(3, width=300)
    create_clicked = action_cols[0].button(
        "Создать",
        type="primary",
    )
    open_disabled = st.session_state.get("selected_trade_id") is None
    open_clicked = action_cols[1].button(
        "Открыть",
        disabled=open_disabled,
    )
    delete_clicked = action_cols[2].button(
        "Удалить",
        disabled=open_disabled,
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

if st.session_state.get("show_create_trade"):
    create_trade_dialog()
if st.session_state.get("show_edit_trade"):
    edit_trade_dialog()
if st.session_state.get("show_delete_trade"):
    delete_trade_dialog()
