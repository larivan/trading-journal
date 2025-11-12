"""Секция заметок и работа с их связями."""

from typing import Any, Dict, List, Optional, Set

import streamlit as st

from db import (
    add_note,
    attach_note_to_trade,
    detach_note_from_trade,
)


def render_notes_section(
    *,
    trade_id: int,
    trade_key: str,
    attached_notes: List[Dict[str, Any]],
    all_notes: List[Dict[str, Any]],
) -> None:
    st.subheader("Notes")
    note_ids = [note["id"] for note in all_notes]
    note_index = {note["id"]: note for note in all_notes}
    for note in attached_notes:
        if note["id"] not in note_index:
            note_index[note["id"]] = note
            note_ids.append(note["id"])
    selected_default = [note["id"] for note in attached_notes]

    c1, c2 = st.columns([0.6, 0.4], vertical_alignment="bottom")
    note_key = f"tm_note_select_{trade_key}"
    selected_note_ids = c1.multiselect(
        "Linked notes",
        options=note_ids,
        default=selected_default,
        key=note_key,
        format_func=lambda note_id: _note_label(note_index.get(note_id)),
    )

    _sync_note_links(
        trade_id=trade_id,
        current_ids=set(selected_default),
        selected_ids=set(selected_note_ids),
    )

    with c2.popover("Add", use_container_width=True):
        new_note_title = st.text_input(
            "Title",
            key=f"tm_note_title_{trade_key}",
        )
        new_note_body = st.text_area(
            "Body",
            height=160,
            key=f"tm_note_body_{trade_key}",
        )
        if st.button(
            "Create note",
            key=f"tm_note_create_{trade_key}",
            use_container_width=True,
        ):
            body_value = new_note_body.strip()
            if not body_value:
                st.warning("Note body cannot be empty.")
            else:
                try:
                    note_id = add_note(
                        new_note_title.strip() or None,
                        body_value,
                    )
                    attach_note_to_trade(trade_id, note_id)
                    st.success("Note created and attached.")
                    st.rerun()
                except Exception as exc:  # pragma: no cover - UI feedback
                    st.error(f"Failed to add note: {exc}")


def _note_label(note: Optional[Dict[str, Any]]) -> str:
    if not note:
        return "Unknown note"
    title = (note.get("title") or "").strip()
    if title:
        return f"{title} (#{note['id']})"
    body = (note.get("body") or "").strip()
    if len(body) > 40:
        body = body[:37].rstrip() + "..."
    return f"{body or 'Untitled'} (#{note['id']})"


def _sync_note_links(
    *,
    trade_id: int,
    current_ids: Set[int],
    selected_ids: Set[int],
) -> None:
    to_attach = selected_ids - current_ids
    to_detach = current_ids - selected_ids
    if not to_attach and not to_detach:
        return
    try:
        for note_id in to_attach:
            attach_note_to_trade(trade_id, note_id)
        for note_id in to_detach:
            detach_note_from_trade(trade_id, note_id)
        st.success("Notes updated.")
        st.rerun()
    except Exception as exc:  # pragma: no cover - UI feedback
        st.error(f"Failed to update notes: {exc}")
