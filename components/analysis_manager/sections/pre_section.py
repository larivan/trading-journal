"""Секция редактирования этапа Pre-market."""

from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

from components.chart_editor import (
    chart_table_rows,
    render_chart_editor,
)
from config import DAILY_BIAS, ASSETS
from db import (
    list_analysis_stage_charts,
)


def render_pre_stage(
    *,
    stage_data: Optional[Dict[str, Any]],
    defaults: Dict[str, Any],
    visible: bool,
    expanded: bool,
) -> Optional[Dict[str, Any]]:
    """Редактирование этапа pre-market."""

    if not visible or not stage_data:
        return None
    stage_id = stage_data["id"]
    with st.expander("Overview & Pre-market", expanded=expanded):
        col1, col2 = st.columns([1, 3], gap="medium")
        with col1:
            date_value = st.date_input(
                "Date",
                value=defaults["date_local"],
                format="DD.MM.YYYY",
                key=f"stage_date_{stage_id}",
            )
            asset_value = st.selectbox(
                "Asset",
                options=ASSETS,
                index=ASSETS.index(defaults["asset"]),
                key=f"stage_asset_{stage_id}",
            )
            st.divider()
            daily_bias_value = st.selectbox(
                "Daily bias",
                options=DAILY_BIAS,
                index=DAILY_BIAS.index(defaults["daily_bias"]),
                key=f"stage_daily_bias_{stage_id}",
            )

        with col2:
            st.markdown("#### Charts")
            charts = list_analysis_stage_charts(stage_id)
            chart_rows_source = chart_table_rows(charts)
            chart_editor_value = render_chart_editor(
                key=f"chart_editor_stage_{stage_id}",
                base_rows=chart_rows_source,
                title="",
                caption=None,
            )
            st.divider()
            summary_value = st.text_area(
                "Analysis Notes",
                value=stage_data.get("summary") or "",
                height=160,
                key=f"stage_summary_{stage_id}",
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
            "attached": charts,
            "rows_source": chart_rows_source,
            "editor_value": chart_editor_value,
        },
    }


__all__ = ["render_pre_stage"]
