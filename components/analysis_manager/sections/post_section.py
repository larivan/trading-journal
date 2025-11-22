"""Секция редактирования этапа post-market."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import streamlit as st

from components.chart_editor import (
    chart_table_rows,
    render_chart_editor,
)
from components.note_editor import render_note_editor
from config import DAILY_BIAS, DAY_RESULT_VALUES
from db import add_note


def render_post_stage(
    *,
    stage_key: str,
    stage_data: Optional[Dict[str, Any]],
    defaults: Dict[str, Any],
    visible: bool,
    expanded: bool,
    all_notes: List[Dict[str, Any]],
    note_state_key: str,
) -> Optional[Dict[str, Any]]:
    """Редактирование этапа post-market."""

    if not visible or not stage_data:
        return None

    stage_id = stage_data.get("stage_id")
    fact_bias_value = defaults.get("fact_bias", DAILY_BIAS[0])
    day_result_value = defaults.get("day_result", DAY_RESULT_VALUES[0])
    if fact_bias_value not in DAILY_BIAS:
        fact_bias_value = DAILY_BIAS[0]
    if day_result_value not in DAY_RESULT_VALUES:
        day_result_value = DAY_RESULT_VALUES[0]

    chart_rows_source = stage_data.get("rows_source") or chart_table_rows(
        stage_data.get("charts") or []
    )
    stage_data["rows_source"] = chart_rows_source

    default_note_ids = list(stage_data.get("note_ids") or [])
    note_ids: List[int] = st.session_state.get(
        note_state_key, list(default_note_ids))
    st.session_state[note_state_key] = note_ids

    note_index = {note["id"]: note for note in all_notes}
    for note in stage_data.get("attached_notes") or []:
        note_index.setdefault(note["id"], note)
    attached_notes = [
        note_index[note_id]
        for note_id in note_ids
        if note_id in note_index
    ]

    def _attach_note(note_id: int) -> None:
        ids = st.session_state.get(note_state_key, note_ids)
        if note_id not in ids:
            ids.append(note_id)
            st.session_state[note_state_key] = ids

    def _detach_note(note_id: int) -> None:
        ids = st.session_state.get(note_state_key, note_ids)
        st.session_state[note_state_key] = [
            nid for nid in ids if nid != note_id]

    with st.expander("Post-market", expanded=expanded):
        col1, col2 = st.columns([1, 3], gap="medium")

        with col1:
            fact_bias_value = st.selectbox(
                "Fact bias",
                options=DAILY_BIAS,
                index=DAILY_BIAS.index(fact_bias_value),
                key=f"{stage_key}_fact_bias",
            )
            day_result_value = st.selectbox(
                "Day result",
                options=DAY_RESULT_VALUES,
                index=DAY_RESULT_VALUES.index(day_result_value),
                key=f"{stage_key}_day_result",
            )

        with col2:
            st.markdown("#### Charts")
            chart_editor_value = render_chart_editor(
                key=f"chart_editor_{stage_key}",
                base_rows=chart_rows_source,
                title="",
                caption=None,
            )

            summary_value = st.text_area(
                "Analysis Notes",
                value=stage_data.get("summary") or "",
                height=160,
                key=f"{stage_key}_summary",
            )

            st.markdown("#### Observations")
            render_note_editor(
                key=f"{stage_key}_notes",
                attached_notes=attached_notes,
                attach_note=_attach_note,
                detach_note=_detach_note,
                create_note=lambda title, body: add_note(title, body),
                all_notes=all_notes,
                selection_label="Связанные заметки",
                popover_label="Создать заметку",
                create_button_label="Добавить",
                empty_warning="Текст заметки не может быть пустым.",
                success_update_message=None,
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
            "attached": stage_data.get("charts") or [],
            "rows_source": chart_rows_source,
            "editor_value": chart_editor_value,
        },
        "notes": {
            "selected_ids": list(st.session_state[note_state_key]),
            "original_ids": stage_data.get("original_note_ids") or [],
        },
    }


__all__ = ["render_post_stage"]
