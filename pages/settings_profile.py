"""Страница профиля пользователя — смена пароля."""

import streamlit as st

from db import get_user_by_id, update_user_password
from utils.auth import (
    get_current_user_id,
    hash_password,
    verify_password,
)

st.set_page_config(
    page_title="Profile",
    page_icon=":material/person:",
    layout="wide",
)

user_id = get_current_user_id()
user = get_user_by_id(user_id) if user_id else None

st.title(":material/person: Profile")

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
