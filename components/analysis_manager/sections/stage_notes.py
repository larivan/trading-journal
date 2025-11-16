"""Компоненты для работы с заметками этапов анализа."""

from __future__ import annotations

from typing import Any, Dict, Optional, Set

import streamlit as st

from db import (
    add_note,
    attach_note_to_analysis_stage,
    detach_note_from_analysis_stage,
    list_analysis_stage_notes,
    list_notes,
)


def render_stage_notes(*, stage_id: int, stage_key: str) -> None:
    """Рисует выбор заметок для этапа и синхронизирует их с БД."""

    attached_notes = list_analysis_stage_notes(stage_id)
    all_notes = list_notes()
    note_ids = [note["id"] for note in all_notes]
    note_index = {note["id"]: note for note in all_notes}
    for note in attached_notes:
        if note["id"] not in note_index:
            note_index[note["id"]] = note
            note_ids.append(note["id"])

    selected_default = [note["id"] for note in attached_notes]
    selected_ids = st.multiselect(
        "Связанные заметки",
        options=note_ids,
        default=selected_default,
        key=f"notes_select_{stage_key}",
        format_func=lambda note_id: _note_label(note_index.get(note_id)),
    )
    _sync_stage_notes(
        stage_id=stage_id,
        current_ids=set(selected_default),
        selected_ids=set(selected_ids),
    )

    with st.popover("Создать заметку", use_container_width=True):
        new_note_title = st.text_input("Title", key=f"note_title_{stage_key}")
        new_note_body = st.text_area("Body", key=f"note_body_{stage_key}", height=160)
        if st.button("Добавить", use_container_width=True, key=f"note_add_{stage_key}"):
            body_value = (new_note_body or "").strip()
            if not body_value:
                st.warning("Текст заметки не может быть пустым.")
            else:
                try:
                    note_id = add_note(new_note_title.strip() or None, body_value)
                    attach_note_to_analysis_stage(stage_id, note_id)
                    st.success("Заметка создана.")
                    st.rerun()
                except Exception as exc:  # pragma: no cover
                    st.error(f"Не удалось создать заметку: {exc}")


def _note_label(note: Optional[Dict[str, Any]]) -> str:
    if not note:
        return "Неизвестная заметка"
    title = (note.get("title") or "").strip()
    if title:
        return f"{title} (#{note['id']})"
    body = (note.get("body") or "").strip()
    if len(body) > 40:
        body = body[:37].rstrip() + "..."
    return f"{body or 'Untitled'} (#{note['id']})"


def _sync_stage_notes(*, stage_id: int, current_ids: Set[int], selected_ids: Set[int]) -> None:
    to_attach = selected_ids - current_ids
    to_detach = current_ids - selected_ids
    if not to_attach and not to_detach:
        return
    try:
        for note_id in to_attach:
            attach_note_to_analysis_stage(stage_id, note_id)
        for note_id in to_detach:
            detach_note_from_analysis_stage(stage_id, note_id)
        st.success("Список заметок обновлён.")
        st.rerun()
    except Exception as exc:  # pragma: no cover
        st.error(f"Не удалось обновить заметки: {exc}")


__all__ = ["render_stage_notes"]
