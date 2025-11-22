"""Диалог создания и редактирования заметок."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import streamlit as st

from config import NOTE_TYPE_VALUES
from db import add_note, get_note, update_note

DialogCallback = Optional[Callable[[int], None]]


def render_note_manager(
    *,
    note_id: Optional[int] = None,
    on_created: DialogCallback = None,
    on_close: Optional[Callable[[], None]] = None,
) -> None:
    """Единое окно для создания и редактирования заметок."""

    dialog_key = _dialog_key(note_id)
    is_new_note = note_id is None
    note: Dict[str, Any] = {}
    note_error: Optional[str] = None
    if not is_new_note:
        if not note_id:
            note_error = "Заметка не выбрана."
        else:
            existing = get_note(note_id)
            if not existing:
                note_error = f"Заметка #{note_id} не найдена."
            else:
                note = existing

    title_value = note.get("title") or ""
    body_value = note.get("body") or ""
    note_type_value = note.get("note_type")
    if note_type_value not in NOTE_TYPE_VALUES:
        note_type_value = None

    dialog_title = "New note" if is_new_note else _format_dialog_title(note)

    @st.dialog(dialog_title, width="medium")
    def _dialog() -> None:
        if note_error:
            st.warning(note_error)
            return

        title_input = st.text_input(
            "Title",
            value=title_value,
            key=f"{dialog_key}_title",
            placeholder="Optional",
        )
        type_input = st.selectbox(
            "Note type",
            options=["— Not specified —"] + list(NOTE_TYPE_VALUES),
            index=_note_type_index(note_type_value),
            key=f"{dialog_key}_type",
        )
        body_input = st.text_area(
            "Body",
            value=body_value,
            key=f"{dialog_key}_body",
            height=240,
        )

        save_col, cancel_col = st.columns(2)
        save_clicked = save_col.button(
            "Save",
            type="primary",
            use_container_width=True,
        )
        cancel_clicked = cancel_col.button(
            "Cancel",
            use_container_width=True,
            disabled=on_close is None,
        )

        if cancel_clicked and on_close:
            _reset_dialog_state(dialog_key)
            on_close()
            return

        if not save_clicked:
            return

        body_clean = (body_input or "").strip()
        if not body_clean:
            st.warning("Note body cannot be empty.")
            return
        title_clean = (title_input or "").strip() or None
        note_type_clean = _resolve_note_type(type_input)

        try:
            if is_new_note:
                new_note_id = add_note(
                    title_clean,
                    body_clean,
                    note_type_clean,
                )
                _reset_dialog_state(dialog_key)
                if on_created:
                    on_created(new_note_id)
                else:
                    st.rerun()
            else:
                update_note(
                    note.get("id"),
                    title_clean,
                    body_clean,
                    note_type=note_type_clean,
                )
                _reset_dialog_state(dialog_key)
                st.rerun()
        except Exception as exc:  # pragma: no cover - UI feedback
            st.error(f"Не удалось сохранить заметку: {exc}")

    _dialog()


def _note_type_index(value: Optional[str]) -> int:
    if value in NOTE_TYPE_VALUES:
        try:
            return list(NOTE_TYPE_VALUES).index(value) + 1
        except ValueError:
            return 0
    return 0


def _resolve_note_type(selection: str) -> Optional[str]:
    clean = (selection or "").strip()
    if not clean or clean == "— Not specified —":
        return None
    return clean if clean in NOTE_TYPE_VALUES else None


def _format_dialog_title(note: Dict[str, Any]) -> str:
    title = (note.get("title") or "").strip()
    if title:
        return f"{title} (#{note.get('id')})"
    snippet = (note.get("body") or "").strip()
    if len(snippet) > 40:
        snippet = snippet[:37].rstrip() + "..."
    return f"{snippet or 'Note'} (#{note.get('id')})"


def _dialog_key(note_id: Optional[int]) -> str:
    return "note_create" if note_id is None else f"note_edit_{note_id}"


def _reset_dialog_state(dialog_key: str) -> None:
    st.session_state.pop(f"{dialog_key}_title", None)
    st.session_state.pop(f"{dialog_key}_body", None)
    st.session_state.pop(f"{dialog_key}_type", None)


__all__ = ["render_note_manager"]
