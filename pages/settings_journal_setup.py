"""Страница торговых настроек журнала — активы, пороги, риск."""

import pandas as pd
import streamlit as st

from config import ASSETS_VALUES, BE_THRESHOLD
from db import update_user_settings
from utils.auth import get_current_user_id, get_user_settings, load_user_session

st.set_page_config(
    page_title="Journal Setup",
    page_icon=":material/tune:",
    layout="wide",
)

user_id = get_current_user_id()
settings = get_user_settings(user_id) if user_id else {}

st.title(":material/tune: Journal Setup")

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
