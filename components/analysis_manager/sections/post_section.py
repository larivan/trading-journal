"""Секция редактирования этапа post-market."""

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
from components.note_editor import render_note_editor
from config import DAILY_BIAS, DAY_RESULT_VALUES
from db import (
    add_note,
    attach_chart_to_analysis_stage,
    attach_note_to_analysis_stage,
    detach_note_from_analysis_stage,
    list_analysis_stage_charts,
    list_analysis_stage_notes,
    list_notes,
    update_analysis,
    update_analysis_stage,
)


def render_post_stage(
    *,
    stage_data: Optional[Dict[str, Any]],
    analysis: Dict[str, Any],
    analysis_id: int,
    visible: bool,
    expanded: bool,
) -> None:
    """Редактирование этапа post-market."""

    if not visible or not stage_data:
        return
    stage_id = stage_data["id"]
    with st.expander("Post-market", expanded=expanded):
        fact_bias_value = st.selectbox(
            "Fact bias",
            options=DAILY_BIAS,
            index=DAILY_BIAS.index(analysis.get("fact_bias")) if analysis.get("fact_bias") in DAILY_BIAS else 0,
            key=f"stage_fact_bias_{stage_id}",
        )
        day_result_value = st.selectbox(
            "Результат дня",
            options=DAY_RESULT_VALUES,
            index=DAY_RESULT_VALUES.index(analysis.get("day_result")) if analysis.get("day_result") in DAY_RESULT_VALUES else 0,
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
        attached_notes = list_analysis_stage_notes(stage_id)
        render_note_editor(
            key=f"analysis_stage_{stage_id}",
            attached_notes=attached_notes,
            attach_note=lambda note_id, s_id=stage_id: attach_note_to_analysis_stage(s_id, note_id),
            detach_note=lambda note_id, s_id=stage_id: detach_note_from_analysis_stage(s_id, note_id),
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

        if st.button(
            "Сохранить этап",
            type="primary",
            use_container_width=True,
            key=f"save_stage_{stage_id}",
        ):
            stage_payload = {
                "analysis_id": analysis_id,
                "type": "post-market",
                "summary": summary_value.strip() or None,
                "time_local": datetime.now().strftime("%H:%M:%S"),
            }
            try:
                update_analysis_stage(stage_id, stage_payload)
                update_analysis(
                    analysis_id,
                    {
                        "fact_bias": fact_bias_value,
                        "day_result": day_result_value,
                    },
                )
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


__all__ = ["render_post_stage"]
