"""Страница профиля пользователя."""

import streamlit as st

from utils.auth import get_current_user_id

st.set_page_config(
    page_title="Profile",
    page_icon=":material/person:",
    layout="wide",
)

user_id = get_current_user_id()

st.title(":material/person: Profile")

st.text_input("Email", value=st.user.email if st.user.is_logged_in else "", disabled=True)
st.text_input("Name", value=getattr(st.user, "name", "") or "", disabled=True)
st.caption("Profile information is managed by your Google account.")
