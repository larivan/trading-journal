"""Страница настроек с вкладками: Profile, Journal Setup, Preferences, Backup."""

from datetime import datetime

import pandas as pd
import pytz
import streamlit as st

from config import ASSETS_VALUES, BE_THRESHOLD
from db import update_user_settings
from utils.auth import get_current_user_id, get_user_settings, load_user_session
from utils.backup import create_backup, get_backup_bytes, list_backups
from utils.cached_data import cached_accounts
from helpers import to_option_format, custom_selectbox

st.set_page_config(page_title="Settings", page_icon=":material/settings:", layout="wide")
st.title(":material/settings: Settings")

user_id = get_current_user_id()
settings = get_user_settings(user_id) if user_id else {}

tab_profile, tab_journal, tab_prefs, tab_backup = st.tabs(
    ["Profile", "Journal Setup", "Preferences", "Backup"]
)

# =====================================================================
# Profile
# =====================================================================
with tab_profile:
    st.text_input("Email", value=st.user.email if st.user.is_logged_in else "", disabled=True)
    st.text_input("Name", value=getattr(st.user, "name", "") or "", disabled=True)
    st.caption("Profile information is managed by your Google account.")

# =====================================================================
# Journal Setup
# =====================================================================
with tab_journal:
    col_assets, col_thresh = st.columns([0.45, 0.55])

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
        if not new_assets:
            st.error("Asset list cannot be empty.")
        elif risk_min >= risk_max:
            st.error("Risk min must be less than Risk max.")
        else:
            update_user_settings(user_id, {
                "assets": new_assets,
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
        selected_currency = st.selectbox(
            "Currency",
            ["USD", "EUR", "GBP", "RUB", "JPY", "CHF"],
            index=["USD", "EUR", "GBP", "RUB", "JPY", "CHF"].index(
                settings.get("currency", "USD")
            ),
        )

        if st.button("Save localization"):
            update_user_settings(user_id, {
                "local_tz": selected_tz,
                "currency": selected_currency,
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
