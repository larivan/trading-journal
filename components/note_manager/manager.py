"""Диалог создания и редактирования заметок."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

import streamlit as st

from components.image_editor import (
    image_table_rows,
    persist_image_editor,
    render_image_editor,
)
from config import (
    NOTE_DIALOG_NAME,
    NOTE_ID_STATE,
    NOTE_MANAGER_KEY_PREFIX,
    NOTE_SUCCESS_STATE,
)
from db import (
    attach_image_to_note,
    create_note,
    transaction,
    update_note,
)
from utils.auth import get_current_user_id
from utils.cached_data import (
    cached_images,
    cached_note,
    cached_notes,
    cached_notes_count_by_trade,
    cached_trades,
)
from utils.session_state import (
    open_dialog,
    close_dialog,
    dialog_is_active,
    get_previous_dialog,
    remove_previous_dialog,
)
from helpers import parse_date

_NOTE_CATEGORIES = ["Note", "Observation", "Hypothesis"]


def render_note_manager() -> None:
    """Рендерит диалог для создания и редактирования заметок."""
    if NOTE_SUCCESS_STATE in st.session_state:
        st.toast(st.session_state.pop(NOTE_SUCCESS_STATE), icon="🔥")

    if not dialog_is_active(NOTE_DIALOG_NAME):
        return

    user_id = get_current_user_id()
    note_id = st.session_state.get(NOTE_ID_STATE)
    is_new_note = note_id is None
    note: Dict[str, Any] = {}

    if not is_new_note:
        note = cached_note(note_id, user_id) or {}
        if not note:
            st.error("Note not found.")
            st.session_state.pop(NOTE_ID_STATE, None)
            close_dialog()
            st.rerun()
            return

    state_key = f"{NOTE_MANAGER_KEY_PREFIX}{note_id or 'new'}"
    images: List[Dict[str, Any]] = cached_images(note_id=note_id) if note_id else []

    _notes_by_trade = cached_notes_count_by_trade(user_id) if not is_new_note else {}
    _all_trades = cached_trades(user_id) if not is_new_note else []
    _total_trades = len(_all_trades) if _all_trades else 0
    _linked_trade_count = _notes_by_trade.get(int(note_id), 0) if note_id else 0
    _oor = _linked_trade_count / _total_trades * 100 if _total_trades else 0.0

    @st.dialog(
        _get_dialog_title(note, is_new_note),
        width="medium",
        on_dismiss=_handle_dialog_dismiss,
    )
    def _dialog() -> None:
        image_values = render_image_editor(
            key=f"{state_key}_charts",
            base_rows=image_table_rows(images),
            layout_columns=2,
        )

        body_value = st.text_area(
            "Content",
            value=note.get("body") or "",
            height=200,
            key=f"{state_key}_body",
            placeholder="Write your note…",
        )

        if is_new_note:
            category_value = st.pills(
                "Category",
                options=_NOTE_CATEGORIES,
                default=_NOTE_CATEGORIES[0],
                selection_mode="single",
                label_visibility="collapsed",
                key=f"{state_key}_category",
            )
        else:
            category_value = note.get("category")
            meta_parts = []
            if category_value:
                meta_parts.append(f":material/label: {category_value}")
            trades_label = f"{_linked_trade_count} trade{'s' if _linked_trade_count != 1 else ''}"
            oor_label = f"{_oor:.1f}%"
            meta_parts.append(f":material/link: {trades_label} linked · OOR: {oor_label}")
            st.caption("  ·  ".join(meta_parts))

        st.divider()

        if get_previous_dialog():
            actions_col, message_col = st.columns(
                [0.4, 0.6],
                vertical_alignment="bottom",
            )
            with actions_col:
                c1, c2 = st.columns(2)
                if c1.button(":material/arrow_back: Back", width="stretch"):
                    close_dialog()
                    open_dialog(get_previous_dialog())
                    remove_previous_dialog()
                    st.rerun()
                save_clicked = c2.button(
                    "Save",
                    type="primary",
                    width="stretch",
                    key=f"{state_key}_save",
                )
        else:
            actions_col, message_col = st.columns(
                [0.2, 0.8],
                vertical_alignment="bottom",
            )
            with actions_col:
                save_clicked = st.button(
                    "Save",
                    type="primary",
                    width="stretch",
                    key=f"{state_key}_save",
                )

        if save_clicked:
            body_clean = (body_value or "").strip()
            if not body_clean:
                message_col.error("Fill in the content.")
                return

            now = datetime.now()
            payload: Dict[str, Any] = {"body": body_clean}
            if is_new_note:
                payload["date_local"] = now.date().isoformat()
                payload["time_local"] = now.strftime("%H:%M:%S")
                payload["category"] = category_value or _NOTE_CATEGORIES[0]

            try:
                with transaction() as conn:
                    current_note_id = note_id
                    if is_new_note:
                        current_note_id = create_note(user_id, payload, conn=conn)
                    else:
                        update_note(current_note_id, user_id, payload, conn=conn)

                    persist_image_editor(
                        attached_images=images,
                        editor_rows=image_values,
                        conn=conn,
                        attach_image=lambda image_id, note_id=current_note_id: attach_image_to_note(  # noqa: E731
                            note_id, image_id, conn=conn
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

            cached_notes.clear()
            st.rerun()

    if dialog_is_active(NOTE_DIALOG_NAME):
        _dialog()


def _get_dialog_title(data: Dict[str, Any], is_new: bool) -> str:
    if is_new:
        return "New note"
    if not data:
        return "-"
    body = (data.get("body") or "").strip()
    excerpt = (body[:40] + "…") if len(body) > 40 else body
    parsed_date = parse_date(data.get("date_local"))
    formatted_date = parsed_date.strftime("%d.%m.%Y") if parsed_date else ""
    return f"{excerpt}{f' · {formatted_date}' if formatted_date else ''}" if excerpt else f"Note{f' · {formatted_date}' if formatted_date else ''}"


def _handle_dialog_dismiss() -> None:
    st.session_state.pop(NOTE_ID_STATE, None)
    close_dialog()


__all__ = ["render_note_manager"]
