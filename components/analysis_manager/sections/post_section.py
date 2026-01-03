"""Секция редактирования этапа post-market."""
from __future__ import annotations
import streamlit as st
from typing import Any, Dict, List, Optional
from config import DAILY_BIAS_VALUES, DAY_RESULT_VALUES
from helpers import safe_choice_index
from components.chart_editor import (
    chart_table_rows,
    render_chart_editor,
)
from components.note_selector import render_note_selector


def render_post_stage(
    *,
    stage_data: Optional[Dict[str, Any]],
    defaults: Dict[str, Any],
    visible: bool,
    expanded: bool,
    state_key: str
) -> Optional[Dict[str, Any]]:
    """Редактирование этапа post-market."""

    if not visible:
        return None, None

    analysis_result = {}
    stage_result = {
        "stage_id": stage_data.get("stage_id"),
        "stage_type": "post-market",
    }
    chart_rows = chart_table_rows(stage_data.get("charts"))
    with st.expander("Post-market", expanded=expanded):
        col1, col2 = st.columns([1, 3], gap="medium")

        with col1:
            analysis_result["fact_bias"] = st.selectbox(
                "Fact bias",
                options=DAILY_BIAS_VALUES,
                placeholder="- Not set -",
                key=f"{state_key}_fact_bias",
                index=safe_choice_index(
                    DAILY_BIAS_VALUES, defaults.get("fact_bias")),
            )
            analysis_result["day_result"] = st.selectbox(
                "Day result",
                options=DAY_RESULT_VALUES,
                placeholder="- Not set -",
                key=f"{state_key}_day_result",
                index=safe_choice_index(
                    DAY_RESULT_VALUES, defaults.get("day_result")),
            )
            stage_result["summary"] = st.text_area(
                "Summary",
                key=f"{state_key}_summary",
                value=stage_data.get("summary") or "",
                height=100,
            )

        with col2:
            st.markdown("#### Charts")
            chart_editor_value = render_chart_editor(
                key=f"{state_key}_chart_editor",
                base_rows=chart_rows,
                layout_columns=2
            )

            st.markdown("#### Observations")
            staged_note_ids = render_note_selector(
                entity_type="analysis_stage",
                entity_id=stage_data.get("stage_id") if stage_data else None,
                state_key=f"{state_key}_note_selector",
                previous_dialog_name=None,
                excerpt_limit=120,
                base_notes=stage_data.get("notes") if stage_data else None,
            )

        stage_result["charts"] = {
            "attached": stage_data.get("charts") or [],
            "rows_source": chart_rows,
            "editor_value": chart_editor_value,
        }
        stage_result["notes"] = {
            "base_notes": stage_data.get("notes") if stage_data else [],
            "staged_note_ids": staged_note_ids,
        }
    return analysis_result, stage_result


__all__ = ["render_post_stage"]
