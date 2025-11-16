"""Секция редактирования этапа Pre-market."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import streamlit as st

from components.chart_editor import (
    chart_table_rows,
    normalize_editor_rows,
    persist_chart_editor,
    render_chart_editor,
)
from config import DAILY_BIAS
from db import (
    attach_chart_to_analysis_stage,
    list_analysis_stage_charts,
    update_analysis,
    update_analysis_stage,
)


def render_pre_stage(
    *,
    stage_data: Optional[Dict[str, Any]],
    analysis: Dict[str, Any],
    analysis_id: int,
    visible: bool,
    expanded: bool,
) -> None:
    """Редактирование этапа pre-market."""

    if not visible or not stage_data:
        return
    stage_id = stage_data["id"]
    with st.expander("Pre-market", expanded=expanded):
        daily_bias_value = st.selectbox(
            "Daily bias",
            options=DAILY_BIAS,
            index=DAILY_BIAS.index(analysis.get("daily_bias")) if analysis.get("daily_bias") in DAILY_BIAS else 0,
            key=f"stage_daily_bias_{stage_id}",
        )
        summary_value = st.text_area(
            "Описание",
            value=stage_data.get("summary") or "",
            height=220,
            key=f"stage_summary_{stage_id}",
        )

        st.markdown("#### Чарты")
        charts = list_analysis_stage_charts(stage_id)
        chart_rows_source = chart_table_rows(charts)
        chart_editor_value = render_chart_editor(
            key=f"chart_editor_stage_{stage_id}",
            base_rows=chart_rows_source,
            title="",
            caption=None,
        )

        if st.button(
            "Сохранить этап",
            type="primary",
            use_container_width=True,
            key=f"save_stage_{stage_id}",
        ):
            stage_payload = {
                "analysis_id": analysis_id,
                "type": "pre-market",
                "summary": summary_value.strip() or None,
                "time_local": datetime.now().strftime("%H:%M:%S"),
            }
            try:
                update_analysis_stage(stage_id, stage_payload)
                update_analysis(analysis_id, {"daily_bias": daily_bias_value})
                chart_state_payload = chart_editor_value if chart_editor_value is not None else chart_rows_source
                editor_rows = normalize_editor_rows(chart_state_payload)
                persist_chart_editor(
                    attached_charts=charts,
                    editor_rows=editor_rows,
                    attach_chart=lambda chart_id, s_id=stage_id: attach_chart_to_analysis_stage(s_id, chart_id),
                )
                st.success("Этап обновлён.")
                st.rerun()
            except Exception as exc:  # pragma: no cover
                st.error(f"Не удалось сохранить этап: {exc}")


__all__ = ["render_pre_stage"]
