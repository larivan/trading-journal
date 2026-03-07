"""Страница настроек с вкладками: Profile, Accounts, Setups, Journal Setup, Preferences, Backup."""

import sqlite3
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import pytz
import streamlit as st

from components.account_manager import render_account_manager
from components.entity_gallery import render_entity_gallery
from components.setup_manager import render_setup_manager
from config import (
    ACCOUNT_DIALOG_NAME,
    ACCOUNT_ID_STATE,
    ASSETS_VALUES,
    BE_THRESHOLD,
    DEFAULT_MISTAKE_TYPES,
    SETUP_DIALOG_NAME,
    SETUP_ID_STATE,
)
from db import delete_account, delete_setup, list_accounts, update_user_settings
from helpers import custom_selectbox, get_excerpt, to_option_format
from utils.auth import get_current_user_id, get_user_settings, load_user_session
from utils.backup import create_backup, get_backup_bytes, list_backups
from utils.cached_data import cached_accounts, cached_setups, cached_trades, filter_setups
from utils.session_state import open_dialog

st.set_page_config(page_title="Settings", page_icon=":material/settings:", layout="wide")
st.title(":material/settings: Settings")

user_id = get_current_user_id()
settings = get_user_settings(user_id) if user_id else {}

tab_profile, tab_accounts, tab_setups, tab_journal, tab_prefs, tab_backup = st.tabs(
    ["Profile", "Accounts", "Setups", "Journal Setup", "Preferences", "Backup"]
)

# =====================================================================
# Profile
# =====================================================================
with tab_profile:
    st.text_input("Email", value=st.user.email if st.user.is_logged_in else "", disabled=True)
    st.text_input("Name", value=getattr(st.user, "name", "") or "", disabled=True)
    st.caption("Profile information is managed by your Google account.")

# =====================================================================
# Accounts
# =====================================================================
@st.dialog("Delete accounts")
def _confirm_delete_accounts(ids: List[Any], name_map: Dict[int, str]) -> None:
    n = len(ids)
    st.warning(f"Delete {n} account{'s' if n > 1 else ''}? This cannot be undone.")
    for aid in ids:
        st.text(f"• {name_map.get(int(aid), f'#{aid}')}")
    st.caption("Accounts with trades cannot be deleted.")
    col1, col2 = st.columns(2)
    if col1.button("Delete", type="primary", width="stretch"):
        blocked = []
        for aid in ids:
            try:
                delete_account(int(aid), user_id)
            except sqlite3.IntegrityError:
                blocked.append(name_map.get(int(aid), f"#{aid}"))
            except (ValueError, sqlite3.Error) as exc:
                st.toast(f"Failed to delete account: {exc}", icon="❌")
        st.session_state.pop("_pending_delete_account_ids", None)
        st.session_state.pop("settings_accounts_gallery", None)
        st.cache_data.clear()
        if blocked:
            names = ", ".join(f'"{name}"' for name in blocked)
            st.toast(f"Cannot delete {names}: account has trades", icon="⚠️")
        st.rerun()
    if col2.button("Cancel", width="stretch"):
        st.session_state.pop("_pending_delete_account_ids", None)
        st.rerun()


with tab_accounts:
    actions_col, _ = st.columns([0.2, 0.8])
    with actions_col:
        if st.button("Create", type="primary", width="stretch", key="settings_accounts_create"):
            st.session_state.pop(ACCOUNT_ID_STATE, None)
            open_dialog(ACCOUNT_DIALOG_NAME)

    account_rows = list_accounts(user_id, include_archived=True)

    trades_all = cached_trades(user_id)
    account_pnl: Dict[int, float] = {}
    for _t in trades_all:
        _aid = _t.get("account_id")
        _pnl = _t.get("net_pnl")
        if _aid is not None and _pnl is not None:
            account_pnl[_aid] = account_pnl.get(_aid, 0.0) + _pnl

    account_columns: List[Dict[str, Any]] = [
        {"field": "name", "label": "Name", "id": "name", "role": "title"},
        {
            "field": None,
            "label": "",
            "id": "archived_label",
            "role": "subtitle",
            "compute": lambda row: "Archived" if row.get("archived") else "",
        },
        {"field": "broker", "label": "Broker", "id": "broker"},
        {
            "field": None,
            "label": "Starting balance",
            "id": "starting_balance",
            "compute": lambda row: (
                f"{row.get('currency') or 'USD'} {float(row.get('starting_balance') or 0):,.2f}"
                if row.get("starting_balance") is not None else ""
            ),
        },
        {
            "field": None,
            "label": "Current balance",
            "id": "current_balance",
            "compute": lambda row: (
                f"{row.get('currency') or 'USD'} {(row.get('starting_balance') or 0) + account_pnl.get(row['id'], 0.0):,.2f}"
            ),
        },
    ]

    def _open_account(row: Dict[str, Any]) -> None:
        account_id = row.get("id")
        if account_id is None:
            return
        st.session_state[ACCOUNT_ID_STATE] = account_id
        open_dialog(ACCOUNT_DIALOG_NAME)

    def _delete_accounts(ids: List[Any]) -> None:
        if not ids:
            return
        st.session_state["_pending_delete_account_ids"] = ids
        st.rerun()

    render_entity_gallery(
        entity_name="account",
        key="settings_accounts_gallery",
        rows=account_rows,
        columns=account_columns,
        empty_message="No accounts found.",
        page_size=9,
        on_open=_open_account,
        on_delete=_delete_accounts,
    )
    render_account_manager()

    pending = st.session_state.get("_pending_delete_account_ids")
    if pending:
        _confirm_delete_accounts(pending, {acc["id"]: acc["name"] for acc in account_rows})

# =====================================================================
# Setups
# =====================================================================
with tab_setups:
    search_col, _, actions_col = st.columns([0.6, 0.2, 0.2])

    with search_col:
        setups_query = st.text_input(
            "Search",
            value="",
            key="settings_setups_search_query",
            placeholder="Type to search...",
        ).strip()

    with actions_col:
        if st.button("Create", type="primary", width="stretch", key="settings_setups_create"):
            st.session_state.pop(SETUP_ID_STATE, None)
            open_dialog(SETUP_DIALOG_NAME)

    setups_filters: Dict[str, Any] = {}
    if setups_query:
        setups_filters["query"] = setups_query

    setup_rows = filter_setups(cached_setups(user_id), setups_filters, order_by="name", ascending=True)

    setup_columns: List[Dict[str, Any]] = [
        {"field": "name", "label": "Setup", "id": "name", "role": "title"},
        {
            "field": "description",
            "label": "Description",
            "id": "description",
            "role": "text",
            "format": lambda value: get_excerpt(value, 140),
        },
    ]

    def _open_setup(row: Dict[str, Any]) -> None:
        setup_id = row.get("id")
        if setup_id is None:
            return
        st.session_state[SETUP_ID_STATE] = setup_id
        open_dialog(SETUP_DIALOG_NAME)

    def _delete_setups(ids: List[Any]) -> None:
        if not ids:
            return
        for setup_id in ids:
            try:
                delete_setup(int(setup_id), user_id)
            except (ValueError, sqlite3.Error) as exc:
                st.toast(f"Failed to delete setup #{setup_id}: {exc}", icon="❌")
        st.cache_data.clear()
        st.rerun()

    render_entity_gallery(
        entity_name="setup",
        key="settings_setups_gallery",
        rows=setup_rows,
        columns=setup_columns,
        empty_message="No setups yet.",
        page_size=12,
        on_open=_open_setup,
        on_delete=_delete_setups,
    )
    render_setup_manager()

# =====================================================================
# Journal Setup
# =====================================================================
with tab_journal:
    col_assets, col_mistakes, col_thresh = st.columns([0.3, 0.3, 0.4])

    with col_assets:
        st.markdown("##### Assets")
        current_assets = settings.get("assets", ASSETS_VALUES)
        if not isinstance(current_assets, list):
            current_assets = ASSETS_VALUES

        assets_df = pd.DataFrame({"Asset": current_assets})
        edited_assets_df = st.data_editor(
            assets_df,
            num_rows="dynamic",
            use_container_width=True,
            key="settings_assets_editor",
        )

    with col_mistakes:
        st.markdown("##### Mistake types")
        current_mistakes = settings.get("mistake_types", DEFAULT_MISTAKE_TYPES)
        if not isinstance(current_mistakes, list):
            current_mistakes = DEFAULT_MISTAKE_TYPES

        mistakes_df = pd.DataFrame({"Type": current_mistakes})
        edited_mistakes_df = st.data_editor(
            mistakes_df,
            num_rows="dynamic",
            use_container_width=True,
            key="settings_mistakes_editor",
        )

    with col_thresh:
        st.markdown("##### Thresholds")
        col1, col2, col3 = st.columns(3)
        be_threshold = col1.number_input(
            "BE Threshold",
            value=float(settings.get("be_threshold", BE_THRESHOLD)),
            step=0.01,
            min_value=0.0,
            max_value=0.5,
            format="%.2f",
            help="Trades with |RR| ≤ threshold are considered Break-even",
        )
        risk_min = col2.number_input(
            "Risk min, %",
            value=float(settings.get("risk_min", 0.5)),
            step=0.1,
            min_value=0.1,
            format="%.1f",
        )
        risk_max = col3.number_input(
            "Risk max, %",
            value=float(settings.get("risk_max", 2.0)),
            step=0.1,
            min_value=0.1,
            format="%.1f",
        )

    st.markdown("#### Defaults for new trade")
    def_col1, def_col2 = st.columns(2)
    current_default_asset = settings.get("default_asset")
    current_default_account_id = settings.get("default_account_id")

    assets_for_default = ["—"] + current_assets
    default_asset_idx = 0
    if current_default_asset in assets_for_default:
        default_asset_idx = assets_for_default.index(current_default_asset)
    new_default_asset = def_col1.selectbox("Default asset", assets_for_default, index=default_asset_idx)

    account_rows = cached_accounts(user_id)
    accounts_opts = [{"label": "—", "value": None}] + to_option_format(account_rows, formatter=lambda a: a["name"])
    with def_col2:
        new_default_account_id = custom_selectbox(
            "Default account", accounts_opts, value=current_default_account_id, key="settings_default_account"
        )

    if st.button("Save trading settings", type="primary"):
        new_assets = [
            str(a).strip()
            for a in edited_assets_df["Asset"].tolist()
            if str(a).strip()
        ]
        new_mistake_types = [
            str(m).strip()
            for m in edited_mistakes_df["Type"].tolist()
            if str(m).strip()
        ]
        if not new_assets:
            st.error("Asset list cannot be empty.")
        elif risk_min >= risk_max:
            st.error("Risk min must be less than Risk max.")
        else:
            update_user_settings(user_id, {
                "assets": new_assets,
                "mistake_types": new_mistake_types,
                "be_threshold": be_threshold,
                "risk_min": risk_min,
                "risk_max": risk_max,
                "default_asset": None if new_default_asset == "—" else new_default_asset,
                "default_account_id": new_default_account_id,
            })
            load_user_session(user_id)
            st.success("Trading settings saved.")
            st.rerun()

# =====================================================================
# Preferences
# =====================================================================
with tab_prefs:
    col_loc, col_iface = st.columns([0.5, 0.5])

    with col_loc:
        st.markdown("##### Localization")
        all_timezones = sorted(pytz.all_timezones)
        current_tz = settings.get("local_tz", "Europe/Moscow")
        tz_index = None
        for i, tz in enumerate(all_timezones):
            if tz == current_tz:
                tz_index = i
                break

        selected_tz = st.selectbox(
            "Timezone",
            all_timezones,
            index=tz_index,
            help="Used for trade session detection",
        )
        if st.button("Save localization"):
            update_user_settings(user_id, {
                "local_tz": selected_tz,
            })
            load_user_session(user_id)
            st.success("Localization saved.")

    with col_iface:
        st.markdown("##### Interface")
        current_language = settings.get("language", "en")
        selected_language = st.selectbox(
            "Language",
            ["en", "ru"],
            index=["en", "ru"].index(current_language) if current_language in ["en", "ru"] else 0,
            format_func=lambda x: "English" if x == "en" else "Русский",
        )

        if st.button("Save interface settings"):
            update_user_settings(user_id, {"language": selected_language})
            load_user_session(user_id)
            st.success("Interface settings saved.")

# =====================================================================
# Backup
# =====================================================================
with tab_backup:
    col_create, col_info = st.columns([0.3, 0.7])
    with col_create:
        if st.button("Create backup now", type="primary"):
            try:
                path = create_backup()
                st.success(f"Backup created: {path.name}")
                st.rerun()
            except Exception as exc:
                st.error(f"Backup failed: {exc}")

    col_list, col_restore = st.columns([0.55, 0.45])

    with col_list:
        backups = list_backups()
        if not backups:
            st.info("No backups yet.")
        else:
            st.markdown(f"**{len(backups)} backup(s) stored**")
            for bp in backups:
                size_kb = bp.stat().st_size / 1024
                try:
                    ts = datetime.strptime(
                        bp.stem.replace("journal_backup_", ""), "%Y%m%d_%H%M%S"
                    )
                    label = ts.strftime("%b %d, %Y  %H:%M:%S")
                except ValueError:
                    label = bp.stem
                b_col1, b_col2 = st.columns([0.7, 0.3])
                b_col1.text(f"{label}  ({size_kb:.1f} KB)")
                b_col2.download_button(
                    label="Download",
                    data=get_backup_bytes(bp),
                    file_name=bp.name,
                    mime="application/octet-stream",
                    key=f"download_{bp.name}",
                )

    with col_restore:
        st.markdown("##### Restore from file")
        st.warning(
            "Restoring will overwrite the current database. "
            "Make sure to create a backup first."
        )
        uploaded = st.file_uploader(
            "Upload backup file (.db)",
            type=["db"],
            key="restore_uploader",
        )
        if uploaded:
            if st.button("Restore database", type="secondary"):
                from db.connection import DB_PATH
                try:
                    with open(DB_PATH, "wb") as f:
                        f.write(uploaded.read())
                    st.success("Database restored. Please restart the application.")
                except Exception as exc:
                    st.error(f"Restore failed: {exc}")
