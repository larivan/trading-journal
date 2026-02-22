"""Страница настроек пользователя."""

import streamlit as st
import pytz

from db import get_user_by_id, update_user_settings, update_user_password
from utils.auth import (
    get_current_user_id,
    get_user_settings,
    hash_password,
    verify_password,
    load_user_session,
)
from utils.backup import create_backup, list_backups, get_backup_bytes
from config import ASSETS_VALUES, BE_THRESHOLD

st.set_page_config(
    page_title="Settings",
    page_icon=":material/settings:",
    layout="centered",
)

user_id = get_current_user_id()
user = get_user_by_id(user_id) if user_id else None
settings = get_user_settings(user_id) if user_id else {}

st.title(":material/settings: Settings")

# =====================================================================
# Профиль
# =====================================================================
with st.expander("Profile", expanded=True):
    st.text_input("Username", value=user.get("username", "") if user else "", disabled=True)
    st.markdown("##### Change password")
    with st.form("change_password_form"):
        current_pw = st.text_input("Current password", type="password")
        new_pw = st.text_input("New password", type="password")
        confirm_pw = st.text_input("Confirm new password", type="password")
        pw_submitted = st.form_submit_button("Update password")

    if pw_submitted:
        if not current_pw or not new_pw or not confirm_pw:
            st.error("All fields are required.")
        elif not verify_password(current_pw, user["password_hash"]):
            st.error("Current password is incorrect.")
        elif new_pw != confirm_pw:
            st.error("New passwords do not match.")
        elif len(new_pw) < 6:
            st.error("Password must be at least 6 characters.")
        else:
            update_user_password(user_id, hash_password(new_pw))
            st.success("Password updated.")

# =====================================================================
# Торговые настройки
# =====================================================================
with st.expander("Trading settings", expanded=True):
    st.markdown("##### Assets")
    current_assets = settings.get("assets", ASSETS_VALUES)
    if not isinstance(current_assets, list):
        current_assets = ASSETS_VALUES

    import pandas as pd
    assets_df = pd.DataFrame({"Asset": current_assets})
    edited_assets_df = st.data_editor(
        assets_df,
        num_rows="dynamic",
        use_container_width=True,
        key="settings_assets_editor",
    )

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
            })
            load_user_session(user_id)
            st.success("Trading settings saved.")
            st.rerun()

# =====================================================================
# Локализация
# =====================================================================
with st.expander("Localization"):
    all_timezones = sorted(pytz.all_timezones)
    current_tz = settings.get("local_tz", "UTC+3")
    # Попытаться найти в списке pytz
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

# =====================================================================
# Интерфейс
# =====================================================================
with st.expander("Interface"):
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
# Бекапы
# =====================================================================
with st.expander("Backups"):
    col_create, col_info = st.columns([0.3, 0.7])
    with col_create:
        if st.button("Create backup now", type="primary"):
            try:
                path = create_backup()
                st.success(f"Backup created: {path.name}")
                st.rerun()
            except Exception as exc:
                st.error(f"Backup failed: {exc}")

    backups = list_backups()
    if not backups:
        st.info("No backups yet.")
    else:
        st.markdown(f"**{len(backups)} backup(s) stored**")
        for bp in backups:
            size_kb = bp.stat().st_size / 1024
            b_col1, b_col2 = st.columns([0.7, 0.3])
            b_col1.text(f"{bp.name}  ({size_kb:.1f} KB)")
            b_col2.download_button(
                label="Download",
                data=get_backup_bytes(bp),
                file_name=bp.name,
                mime="application/octet-stream",
                key=f"download_{bp.name}",
            )

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
