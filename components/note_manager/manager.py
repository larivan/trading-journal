"""Диалог создания и редактирования заметок."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

import streamlit as st

from components.chart_editor import (
    chart_table_rows,
    persist_chart_editor,
    render_chart_editor,
)
from config import (
    NOTE_DIALOG_NAME,
    NOTE_ID_STATE,
    NOTE_MANAGER_KEY_PREFIX,
    NOTE_SUCCESS_STATE,
)
from db import (
    attach_chart_to_note,
    create_note,
    get_note,
    list_charts,
    transaction,
    update_note,
)
from helpers import parse_date
from utils.session_state import close_dialog, dialog_is_active


def render_note_manager() -> None:
    """Рендерит диалог для создания и редактирования заметок."""
    if NOTE_SUCCESS_STATE in st.session_state:
        st.toast(st.session_state.pop(NOTE_SUCCESS_STATE), icon="🔥")

    if not dialog_is_active(NOTE_DIALOG_NAME):
        return

    note_id = st.session_state.get(NOTE_ID_STATE)
    is_new_note = note_id is None
    note: Dict[str, Any] = {}

    if not is_new_note:
        note = get_note(note_id) or {}
        if not note:
            st.error("Note not found.")
            st.session_state.pop(NOTE_ID_STATE, None)
            close_dialog()
            st.rerun()
            return

    state_key = f"{NOTE_MANAGER_KEY_PREFIX}{note_id or 'new'}"
    charts: List[Dict[str, Any]] = list_charts(
        note_id=note_id) if note_id else []

    @st.dialog(
        _get_dialog_title(note, is_new_note),
        width="medium",
        on_dismiss=_handle_dialog_dismiss,
    )
    def _dialog() -> None:
        message_col, actions_col = st.columns(
            [0.7, 0.3],
            vertical_alignment="bottom",
        )
        with actions_col:
            save_clicked = st.button(
                "Save",
                type="primary",
                width="stretch",
                key=f"{state_key}_save",
            )

        title_value = st.text_input(
            "Title",
            value=note.get("title") or "",
            key=f"{state_key}_title",
            placeholder="Optional",
        )
        body_value = st.text_area(
            "Content",
            value=note.get("body") or "",
            height=240,
            key=f"{state_key}_body",
            placeholder="Write your note…",
        )

        chart_values = render_chart_editor(
            key=f"{state_key}_charts",
            base_rows=chart_table_rows(charts),
            layout_columns=2,
        )

        if not save_clicked:
            return

        body_clean = (body_value or "").strip()
        if not body_clean:
            message_col.error("Fill in the content.")
            return

        now_value = datetime.now()
        payload: Dict[str, Any] = {
            "title": (title_value or "").strip() or None,
            "body": body_clean,
            "date_local": now_value.date().isoformat(),
            "time_local": now_value.strftime("%H:%M:%S"),
        }

        try:
            with transaction() as conn:
                current_note_id = note_id
                if is_new_note:
                    current_note_id = create_note(payload, conn=conn)
                else:
                    update_note(current_note_id, payload, conn=conn)

                persist_chart_editor(
                    attached_charts=charts,
                    editor_rows=chart_values,
                    conn=conn,
                    attach_chart=lambda chart_id, note_id=current_note_id: attach_chart_to_note(  # noqa: E731
                        note_id, chart_id, conn=conn
                    ),
                )

            if is_new_note:
                st.session_state[NOTE_ID_STATE] = current_note_id
                st.session_state[NOTE_SUCCESS_STATE] = "Note created."
            else:
                st.session_state[NOTE_SUCCESS_STATE] = "Note saved."
        except Exception as exc:  # pragma: no cover - UI feedback
            message_col.error(f"Failed to save note: {exc}")
            return

        st.rerun()

    if dialog_is_active(NOTE_DIALOG_NAME):
        _dialog()


def _get_dialog_title(data: Dict[str, Any], is_new: bool) -> str:
    if is_new:
        return "New note"
    if not data:
        return "-"
    title = (data.get("title") or "Note").strip() or "Note"
    parsed_date = parse_date(data.get("date_local"))
    formatted_date = parsed_date.strftime("%d.%m.%Y") if parsed_date else ""
    return f"{title}{f' · {formatted_date}' if formatted_date else ''}"


def _handle_dialog_dismiss() -> None:
    st.session_state.pop(NOTE_ID_STATE, None)
    close_dialog()


__all__ = ["render_note_manager"]
