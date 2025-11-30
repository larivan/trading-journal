"""Блок открытия сделки."""

from typing import Any, Dict, List, Optional

import streamlit as st
from config import ASSETS
from helpers import custom_selectbox, safe_choice_index

OptionItem = Dict[str, Any]


def render_main_stage(
    expanded: bool,
    defaults: Dict[str, Any],
    account_options: List[OptionItem],
    analysis_options: List[OptionItem],
    setup_options: List[OptionItem],
) -> Dict[str, Any]:
    """Отрисовывает блок открытия сделки (дата, счёт, сетап и риск)."""
    data = defaults.copy()

    with st.expander("Main details", expanded=expanded):
        oc1, oc2 = st.columns(2)
        data["date"] = oc1.date_input(
            "Date",
            value=data["date"] or "today",
            format="DD.MM.YYYY",
        )
        data["time"] = oc2.time_input(
            "Time",
            value=data["time"],
        )
        data["account"] = custom_selectbox(
            "Account",
            account_options,
            placeholder="- Not set -",
            value=data.get("account"),
        )
        data["asset"] = st.selectbox(
            "Asset",
            ASSETS,
            placeholder="- Not set -",
            index=safe_choice_index(ASSETS, data.get("asset")),
        )
        data["analysis"] = custom_selectbox(
            "Daily analysis",
            analysis_options,
            placeholder="- Not set -",
            value=data.get("analysis"),
        )
        data["setup"] = custom_selectbox(
            "Setup",
            setup_options,
            placeholder="- Not set -",
            value=data.get("setup"),
        )
        data["risk_pct"] = st.slider(
            "Risk per trade, %",
            min_value=0.5,
            max_value=2.0,
            value=float(data["risk_pct"]),
            step=0.1,
        )
    return data
