"""Блок открытия сделки."""

from datetime import date as date_type
from typing import Any, Dict, List, Optional, Callable
import streamlit as st
from config import ASSETS_VALUES
from helpers import custom_selectbox, safe_choice_index
from utils.date_periods import today_in_tz

OptionItem = Dict[str, Any]


def render_main_stage(
    expanded: bool,
    defaults: Dict[str, Any],
    account_options: List[OptionItem],
    analysis_options: List[OptionItem],
    setup_options: List[OptionItem],
    state_key: str,
    on_risk_change: Optional[Callable[[], None]] = None,
    locked_fields: bool = False,
    assets: Optional[List[str]] = None,
    user_tz: Optional[str] = None,
) -> Dict[str, Any]:
    """Отрисовывает блок открытия сделки (дата, счёт, сетап и риск)."""
    data = defaults.copy()
    effective_assets = assets if assets else ASSETS_VALUES
    today = today_in_tz(user_tz)

    with st.expander("Main", expanded=expanded):
        data["is_missed"] = st.toggle(
            "Is trade missed?",
            value=data.get("is_missed", 0),
            key=f"{state_key}_is_missed"
        )
        oc1, oc2 = st.columns(2)
        data["date"] = oc1.date_input(
            "Date*",
            value=data.get("date") or today,
            format="DD.MM.YYYY",
            max_value=today,
            key=f"{state_key}_date"
        )
        data["time"] = oc2.time_input(
            "Time*",
            value=data.get("time") or "now",
            key=f"{state_key}_time"
        )
        data["account"] = custom_selectbox(
            "Account*",
            account_options,
            placeholder="- Not set -",
            value=data.get("account"),
            key=f"{state_key}_account",
        )
        data["asset"] = st.selectbox(
            "Asset*",
            effective_assets,
            placeholder="- Not set -",
            key=f"{state_key}_asset",
            index=safe_choice_index(effective_assets, data.get("asset")),
            disabled=locked_fields,
        )
        data["analysis"] = custom_selectbox(
            "Analysis",
            analysis_options,
            placeholder="- Not set -",
            value=data.get("analysis"),
            key=f"{state_key}_analysis",
            disabled=locked_fields,
        )
        data["setup"] = custom_selectbox(
            "Setup",
            setup_options,
            placeholder="- Not set -",
            value=data.get("setup"),
            key=f"{state_key}_setup"
        )
        data["risk_pct"] = st.slider(
            "Risk per trade, %",
            min_value=0.5,
            max_value=2.0,
            value=float(data["risk_pct"]),
            key=f"{state_key}_risk_pct",
            step=0.1,
            on_change=on_risk_change,
        )
    return data
