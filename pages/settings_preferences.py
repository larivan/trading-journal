"""Страница предпочтений — часовой пояс, валюта, язык."""

import pytz
import streamlit as st

from db import update_user_settings
from utils.auth import get_current_user_id, get_user_settings, load_user_session

st.set_page_config(
    page_title="Preferences",
    page_icon=":material/language:",
    layout="wide",
)

user_id = get_current_user_id()
settings = get_user_settings(user_id) if user_id else {}

st.title(":material/language: Preferences")

col_loc, col_iface = st.columns([0.5, 0.5])

# =====================================================================
# Локализация
# =====================================================================
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

# =====================================================================
# Интерфейс
# =====================================================================
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
