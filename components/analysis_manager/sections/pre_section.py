"""Секция редактирования этапа Pre-market."""
from __future__ import annotations
import streamlit as st
from typing import Any, Dict, Optional
from helpers import parse_date, safe_choice_index
from config import DAILY_BIAS_VALUES, ASSETS_VALUES
from components.chart_editor import (
    chart_table_rows,
    render_chart_editor,
)


def render_pre_stage(
    *,
    stage_data: Optional[Dict[str, Any]],
    analysis_defaults: Dict[str, Any],
    visible: bool,
    expanded: bool,
    state_key: str
) -> Optional[Dict[str, Any]]:
    """Редактирование этапа pre-market."""

    if not visible:
        return None, None

    analysis_result = {}
    stage_result = {
        "stage_id": stage_data.get("stage_id"),
        "stage_type": "pre-market",
    }

    chart_rows = chart_table_rows(stage_data.get("charts"))
    with st.expander("Overview & Pre-market", expanded=expanded):
        col1, col2 = st.columns([1, 3], gap="medium")
        with col1:
            analysis_result['date_local'] = st.date_input(
                "Date",
                value=parse_date(analysis_defaults.get(
                    "date_local")) or "today",
                format="DD.MM.YYYY",
                key=f"{state_key}_date"
            )
            analysis_result['asset'] = st.selectbox(
                "Asset",
                options=ASSETS_VALUES,
                placeholder="- Not set -",
                key=f"{state_key}_asset",
                index=safe_choice_index(
                    ASSETS_VALUES, analysis_defaults.get("asset"))
            )
            st.divider()
            analysis_result['daily_bias'] = st.selectbox(
                "Daily bias",
                options=DAILY_BIAS_VALUES,
                key=f"{state_key}_daily_bias",
                index=safe_choice_index(
                    DAILY_BIAS_VALUES, analysis_defaults.get("daily_bias")),
            )
            stage_result["summary"] = st.text_area(
                "Note",
                value=stage_data.get("summary") or "",
                key=f"{state_key}_summary",
                height=100,
            )

        with col2:
            st.markdown("#### Charts")
            chart_editor_value = render_chart_editor(
                key=f"{state_key}_chart_editor",
                base_rows=chart_rows,
                layout_columns=2,
            )

        stage_result["charts"] = {
            "attached": stage_data.get("charts") or [],
            "rows_source": chart_rows,
            "editor_value": chart_editor_value,
        }

    return analysis_result, stage_result


__all__ = ["render_pre_stage"]
