"""Секция редактирования конкретного этапа анализа."""

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
from config import DAILY_BIAS, DAY_RESULT_VALUES
from db import (
    attach_chart_to_analysis_stage,
    list_analysis_stage_charts,
    update_analysis,
    update_analysis_stage,
)

from ..constants import STAGE_TITLES
from .stage_notes import render_stage_notes


def render_stage_section(
    *,
    stage_type: str,
    stage_data: Optional[Dict[str, Any]],
    analysis: Dict[str, Any],
    analysis_id: int,
    visible: bool,
    expanded: bool,
) -> None:
    """Показывает блок редактирования этапа вместе с заметками и чартами."""

    if not visible or not stage_data:
        return
    stage_id = stage_data["id"]
    label = STAGE_TITLES.get(stage_type, stage_type.title())
    with st.expander(label, expanded=expanded):
        analysis_updates: Dict[str, Any] = {}
        if stage_type == "pre-market":
            analysis_updates["daily_bias"] = st.selectbox(
                "Daily bias",
                options=DAILY_BIAS,
                index=DAILY_BIAS.index(analysis.get("daily_bias"))
                if analysis.get("daily_bias") in DAILY_BIAS
                else 0,
                key=f"stage_daily_bias_{stage_id}",
            )
        if stage_type == "post-market":
            analysis_updates["fact_bias"] = st.selectbox(
                "Fact bias",
                options=DAILY_BIAS,
                index=DAILY_BIAS.index(analysis.get("fact_bias"))
                if analysis.get("fact_bias") in DAILY_BIAS
                else 0,
                key=f"stage_fact_bias_{stage_id}",
            )
            analysis_updates["day_result"] = st.selectbox(
                "Результат дня",
                options=DAY_RESULT_VALUES,
                index=DAY_RESULT_VALUES.index(analysis.get("day_result"))
                if analysis.get("day_result") in DAY_RESULT_VALUES
                else 0,
                key=f"stage_day_result_{stage_id}",
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

        st.markdown("#### Заметки")
        render_stage_notes(stage_id=stage_id, stage_key=f"notes_stage_{stage_id}")

        if st.button(
            "Сохранить этап",
            type="primary",
            use_container_width=True,
            key=f"save_stage_{stage_id}",
        ):
            stage_payload = {
                "analysis_id": analysis_id,
                "type": stage_type,
                "summary": summary_value.strip() or None,
                "time_local": datetime.now().strftime("%H:%M:%S"),
            }
            try:
                update_analysis_stage(stage_id, stage_payload)
                filtered_updates = {
                    key: value for key, value in analysis_updates.items() if value is not None
                }
                if filtered_updates:
                    update_analysis(analysis_id, filtered_updates)
                chart_state_payload = chart_editor_value if chart_editor_value is not None else chart_rows_source
                editor_rows = normalize_editor_rows(chart_state_payload)
                persist_chart_editor(
                    attached_charts=charts,
                    editor_rows=editor_rows,
                    attach_chart=lambda chart_id, s_id=stage_id: attach_chart_to_analysis_stage(
                        s_id, chart_id
                    ),
                )
                st.success("Этап обновлён.")
                st.rerun()
            except Exception as exc:  # pragma: no cover
                st.error(f"Не удалось сохранить этап: {exc}")


__all__ = ["render_stage_section"]
