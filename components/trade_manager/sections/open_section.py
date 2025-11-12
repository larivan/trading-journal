"""Блок открытия сделки."""

from typing import Any, Dict, List

import streamlit as st


def render_open_stage(
    *,
    trade_key: str,
    visible: bool,
    expanded: bool,
    defaults: Dict[str, Any],
    account_labels: List[str],
    assets: List[str],
    analysis_labels: List[str],
    setup_labels: List[str],
) -> Dict[str, Any]:
    """Отрисовывает блок открытия сделки (дата, счёт, сетап и риск)."""

    result = defaults.copy()
    if not visible:
        return result

    with st.expander("Opening details", expanded=expanded):
        oc1, oc2 = st.columns(2)
        result["date"] = oc1.date_input(
            "Date",
            value=result["date"],
            format="DD.MM.YYYY",
            key=f"tm_date_{trade_key}",
        )
        result["time"] = oc2.time_input(
            "Time",
            value=result["time"],
            key=f"tm_time_{trade_key}",
        )

        result["account_label"] = st.selectbox(
            "Account",
            account_labels,
            index=account_labels.index(result["account_label"]),
            key=f"tm_account_{trade_key}",
        )

        result["asset"] = st.selectbox(
            "Asset",
            assets,
            index=assets.index(result["asset"]),
            key=f"tm_asset_{trade_key}",
        )

        result["analysis_label"] = st.selectbox(
            "Daily analysis",
            analysis_labels,
            index=analysis_labels.index(result["analysis_label"]),
            key=f"tm_analysis_{trade_key}",
        )

        result["setup_label"] = st.selectbox(
            "Setup",
            setup_labels,
            index=setup_labels.index(result["setup_label"]),
            key=f"tm_setup_{trade_key}",
        )

        result["risk_pct"] = st.slider(
            "Risk per trade, %",
            min_value=0.5,
            max_value=2.0,
            value=float(result["risk_pct"]),
            step=0.1,
            key=f"tm_risk_{trade_key}",
        )
    return result
