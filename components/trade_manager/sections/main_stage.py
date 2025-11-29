"""Блок открытия сделки."""

from typing import Any, Dict, List

import streamlit as st
from config import ASSETS
from helpers import parse_date, parse_time


def render_main_stage(
    expanded: bool,
    defaults: Dict[str, Any],
    account_options: List[str],
    analysis_options: List[str],
    setup_options: List[str],
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
        data["account"] = st.selectbox(
            "Account",
            account_options,
            placeholder="- Not set -",
            index=account_options.index(
                data["account"]) if data["account"] else None,
        )
        data["asset"] = st.selectbox(
            "Asset",
            ASSETS,
            placeholder="- Not set -",
            index=ASSETS.index(data["asset"]) if data["asset"] else None,
        )
        data["analysis"] = st.selectbox(
            "Daily analysis",
            analysis_options,
            placeholder="- Not set -",
            index=analysis_options.index(
                data["analysis"]) if data["analysis"] else None,
        )
        data["setup"] = st.selectbox(
            "Setup",
            setup_options,
            placeholder="- Not set -",
            index=setup_options.index(
                data["setup"]) if data["setup"] else None,
        )
        data["risk_pct"] = st.slider(
            "Risk per trade, %",
            min_value=0.5,
            max_value=2.0,
            value=float(data["risk_pct"]),
            step=0.1,
        )
    return data
