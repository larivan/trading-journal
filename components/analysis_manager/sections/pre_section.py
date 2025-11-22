"""Секция редактирования этапа Pre-market."""

from __future__ import annotations

from datetime import date as date_cls
from typing import Any, Dict, Optional

import streamlit as st

from components.chart_editor import (
    chart_table_rows,
    render_chart_editor,
)
from config import DAILY_BIAS, ASSETS


def render_pre_stage(
    *,
    stage_key: str,
    stage_data: Optional[Dict[str, Any]],
    analysis_defaults: Dict[str, Any],
    visible: bool,
    expanded: bool,
) -> Optional[Dict[str, Any]]:
    """Редактирование этапа pre-market."""

    if not visible or not stage_data:
        return None

    stage_id = stage_data.get("stage_id")
    date_value = _coerce_date(analysis_defaults.get("date_local"))
    asset_value = analysis_defaults.get("asset", ASSETS[0])
    daily_bias_value = analysis_defaults.get("daily_bias", DAILY_BIAS[0])
    if asset_value not in ASSETS:
        asset_value = ASSETS[0]
    if daily_bias_value not in DAILY_BIAS:
        daily_bias_value = DAILY_BIAS[0]

    chart_rows_source = stage_data.get("rows_source") or chart_table_rows(
        stage_data.get("charts") or []
    )
    stage_data["rows_source"] = chart_rows_source

    with st.expander("Overview & Pre-market", expanded=expanded):
        col1, col2 = st.columns([1, 3], gap="medium")
        with col1:
            date_value = st.date_input(
                "Date",
                value=date_value,
                format="DD.MM.YYYY",
                key=f"{stage_key}_date",
            )
            asset_value = st.selectbox(
                "Asset",
                options=ASSETS,
                index=ASSETS.index(asset_value),
                key=f"{stage_key}_asset",
            )
            st.divider()
            daily_bias_value = st.selectbox(
                "Daily bias",
                options=DAILY_BIAS,
                index=DAILY_BIAS.index(daily_bias_value),
                key=f"{stage_key}_daily_bias",
            )

        with col2:
            st.markdown("#### Charts")
            chart_editor_value = render_chart_editor(
                key=f"chart_editor_{stage_key}",
                base_rows=chart_rows_source,
                title="",
                caption=None,
            )
            st.divider()
            summary_value = st.text_area(
                "Analysis Notes",
                value=stage_data.get("summary") or "",
                height=160,
                key=f"{stage_key}_summary",
            )

    return {
        "stage_id": stage_id,
        "stage_type": "pre-market",
        "summary": summary_value,
        "analysis_updates": {
            "daily_bias": daily_bias_value,
            "asset": asset_value,
            "date_local": date_value.isoformat(),
        },
        "charts": {
            "attached": stage_data.get("charts") or [],
            "rows_source": chart_rows_source,
            "editor_value": chart_editor_value,
        },
    }


def _coerce_date(value: Any) -> date_cls:
    if isinstance(value, date_cls):
        return value
    if isinstance(value, str):
        try:
            return date_cls.fromisoformat(value)
        except ValueError:
            pass
    return date_cls.today()


__all__ = ["render_pre_stage"]
