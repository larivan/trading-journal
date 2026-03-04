"""Блок открытия сделки."""

from datetime import date as date_type
from typing import Any, Dict, List, Optional, Callable
import streamlit as st
from config import ASSETS_VALUES, TRADE_TYPE_VALUES
from helpers import custom_selectbox, safe_choice_index
from utils.date_periods import today_in_tz

OptionItem = Dict[str, Any]


def render_main_stage(
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

    # Строка 1: trade_type (full-width)
    data["trade_type"] = st.selectbox(
        "Trade type",
        TRADE_TYPE_VALUES,
        index=safe_choice_index(TRADE_TYPE_VALUES, data.get("trade_type")) or 0,
        key=f"{state_key}_trade_type",
    )

    # Строка 2: date | time
    r1c1, r1c2 = st.columns(2)
    data["date"] = r1c1.date_input(
        "Date*",
        value=data.get("date") or today,
        format="DD.MM.YYYY",
        max_value=today,
        key=f"{state_key}_date"
    )
    data["time"] = r1c2.time_input(
        "Time*",
        value=data.get("time") or "now",
        key=f"{state_key}_time"
    )

    # Строка 3: account | asset
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        data["account"] = custom_selectbox(
            "Account*",
            account_options,
            placeholder="- Not set -",
            value=data.get("account"),
            key=f"{state_key}_account",
        )
    with r2c2:
        data["asset"] = st.selectbox(
            "Asset*",
            effective_assets,
            placeholder="- Not set -",
            key=f"{state_key}_asset",
            index=safe_choice_index(effective_assets, data.get("asset")),
            disabled=locked_fields,
        )

    # Строка 4: analysis | setup
    r3c1, r3c2 = st.columns(2)
    with r3c1:
        data["analysis"] = custom_selectbox(
            "Analysis",
            analysis_options,
            placeholder="- Not set -",
            value=data.get("analysis"),
            key=f"{state_key}_analysis",
            disabled=locked_fields,
        )
    with r3c2:
        data["setup"] = custom_selectbox(
            "Setup",
            setup_options,
            placeholder="- Not set -",
            value=data.get("setup"),
            key=f"{state_key}_setup",
        )

    # Строка 5: risk_pct (full-width slider)
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
