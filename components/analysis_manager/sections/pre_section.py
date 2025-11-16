"""Секция редактирования этапа Pre-market."""

from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

from components.chart_editor import (
    chart_table_rows,
    render_chart_editor,
)
from config import DAILY_BIAS
from db import (
    list_analysis_stage_charts,
)


def render_pre_stage(
    *,
    stage_data: Optional[Dict[str, Any]],
    analysis: Dict[str, Any],
    visible: bool,
    expanded: bool,
) -> Optional[Dict[str, Any]]:
    """Редактирование этапа pre-market."""

    if not visible or not stage_data:
        return None
    stage_id = stage_data["id"]
    with st.expander("Pre-market", expanded=expanded):
        col1, col2 = st.columns([1, 3], gap="medium")
        with col1:
            daily_bias_value = st.selectbox(
                "Daily bias",
                options=DAILY_BIAS,
                index=DAILY_BIAS.index(analysis.get("daily_bias"))
                if analysis.get("daily_bias") in DAILY_BIAS
                else 0,
                key=f"stage_daily_bias_{stage_id}",
            )
            summary_value = st.text_area(
                "Note",
                value=stage_data.get("summary") or "",
                height=160,
                key=f"stage_summary_{stage_id}",
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

    return {
        "stage_id": stage_id,
        "stage_type": "pre-market",
        "analysis_updates": {"daily_bias": daily_bias_value},
        "summary": summary_value,
        "charts": {
            "attached": charts,
            "rows_source": chart_rows_source,
            "editor_value": chart_editor_value,
        },
    }


__all__ = ["render_pre_stage"]
