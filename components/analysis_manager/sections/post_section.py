"""Секция редактирования этапа post-market."""

from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

from components.chart_editor import (
    chart_table_rows,
    render_chart_editor,
)
from components.note_editor import render_note_editor
from config import DAILY_BIAS, DAY_RESULT_VALUES
from db import (
    add_note,
    attach_note_to_analysis_stage,
    detach_note_from_analysis_stage,
    list_analysis_stage_charts,
    list_analysis_stage_notes,
    list_notes,
)


def render_post_stage(
    *,
    stage_data: Optional[Dict[str, Any]],
    defaults: Dict[str, Any],
    visible: bool,
    expanded: bool,
) -> Optional[Dict[str, Any]]:
    """Редактирование этапа post-market."""

    if not visible or not stage_data:
        return
    stage_id = stage_data["id"]
    with st.expander("Post-market", expanded=expanded):
        col1, col2 = st.columns([1, 3], gap="medium")

        with col1:
            fact_bias_value = st.selectbox(
                "Fact bias",
                options=DAILY_BIAS,
                index=DAILY_BIAS.index(defaults["fact_bias"]),
                key=f"stage_fact_bias_{stage_id}",
            )
            day_result_value = st.selectbox(
                "Day result",
                options=DAY_RESULT_VALUES,
                index=DAY_RESULT_VALUES.index(defaults["day_result"]),
                key=f"stage_day_result_{stage_id}",
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

            summary_value = st.text_area(
                "Analysis Notes",
                value=stage_data.get("summary") or "",
                height=160,
                key=f"stage_summary_{stage_id}",
            )

            st.markdown("#### Observations")
            attached_notes = list_analysis_stage_notes(stage_id)
            render_note_editor(
                key=f"analysis_stage_{stage_id}",
                attached_notes=attached_notes,
                attach_note=lambda note_id, s_id=stage_id: attach_note_to_analysis_stage(
                    s_id, note_id),
                detach_note=lambda note_id, s_id=stage_id: detach_note_from_analysis_stage(
                    s_id, note_id),
                create_note=lambda title, body: add_note(title, body),
                load_notes=list_notes,
                selection_label="Связанные заметки",
                popover_label="Создать заметку",
                create_button_label="Добавить",
                empty_warning="Текст заметки не может быть пустым.",
                success_update_message="Список заметок обновлён.",
                success_create_message="Заметка создана.",
                error_update_message="Не удалось обновить заметки: {exc}",
                error_create_message="Не удалось создать заметку: {exc}",
            )

    return {
        "stage_id": stage_id,
        "stage_type": "post-market",
        "analysis_updates": {
            "fact_bias": fact_bias_value,
            "day_result": day_result_value,
        },
        "summary": summary_value,
        "charts": {
            "attached": charts,
            "rows_source": chart_rows_source,
            "editor_value": chart_editor_value,
        },
    }


__all__ = ["render_post_stage"]
