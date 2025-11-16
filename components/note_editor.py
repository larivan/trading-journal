"""Переиспользуемые UI-компоненты для привязки заметок к различным сущностям."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

import streamlit as st

NoteRecord = Dict[str, Any]
AttachNoteFn = Callable[[int], None]
CreateNoteFn = Callable[[Optional[str], str], int]
LoadNotesFn = Callable[[], List[NoteRecord]]


def render_note_editor(
    *,
    key: str,
    attached_notes: List[NoteRecord],
    attach_note: AttachNoteFn,
    detach_note: AttachNoteFn,
    create_note: CreateNoteFn,
    all_notes: Optional[List[NoteRecord]] = None,
    load_notes: Optional[LoadNotesFn] = None,
    title: Optional[str] = None,
    selection_label: str = "Linked notes",
    popover_label: str = "Create note",
    create_button_label: str = "Create note",
    empty_warning: str = "Note body cannot be empty.",
    success_update_message: Optional[str] = "Notes updated.",
    success_create_message: Optional[str] = "Note created.",
    error_update_message: str = "Failed to update notes: {exc}",
    error_create_message: str = "Failed to create note: {exc}",
    column_ratio: Optional[Sequence[float]] = None,
) -> None:
    """Отрисовывает универсальный селектор заметок с поддержкой связывания и создания."""

    options, note_index = _build_note_options(
        attached_notes=attached_notes,
        all_notes=all_notes,
        load_notes=load_notes,
    )
    selected_default = [note["id"] for note in attached_notes]

    if title:
        st.subheader(title)

    if column_ratio:
        if len(column_ratio) != 2:
            raise ValueError("column_ratio must contain two values when provided.")
        select_container, popover_container = st.columns(
            tuple(column_ratio), vertical_alignment="bottom"
        )
    else:
        select_container = st
        popover_container = st

    selected_ids = select_container.multiselect(
        selection_label,
        options=options,
        default=selected_default,
        key=f"{key}_select",
        format_func=lambda note_id: _note_label(note_index.get(note_id)),
    )

    _sync_note_links(
        attach_note=attach_note,
        detach_note=detach_note,
        current_ids=set(selected_default),
        selected_ids=set(selected_ids),
        success_message=success_update_message,
        error_message_template=error_update_message,
    )

    _render_note_creator(
        container=popover_container,
        key=key,
        popover_label=popover_label,
        create_button_label=create_button_label,
        empty_warning=empty_warning,
        success_message=success_create_message,
        error_message_template=error_create_message,
        create_note=create_note,
        attach_note=attach_note,
    )


def _build_note_options(
    *,
    attached_notes: List[NoteRecord],
    all_notes: Optional[List[NoteRecord]],
    load_notes: Optional[LoadNotesFn],
) -> Tuple[List[int], Dict[int, NoteRecord]]:
    if all_notes is not None:
        note_pool = list(all_notes)
    elif load_notes is not None:
        note_pool = list(load_notes())
    else:
        raise ValueError("Нужно указать либо all_notes, либо load_notes.")

    note_ids = [note["id"] for note in note_pool]
    note_index = {note["id"]: note for note in note_pool}
    for note in attached_notes:
        if note["id"] not in note_index:
            note_index[note["id"]] = note
            note_ids.append(note["id"])
    return note_ids, note_index


def _sync_note_links(
    *,
    attach_note: AttachNoteFn,
    detach_note: AttachNoteFn,
    current_ids: Set[int],
    selected_ids: Set[int],
    success_message: Optional[str],
    error_message_template: str,
) -> None:
    to_attach = selected_ids - current_ids
    to_detach = current_ids - selected_ids
    if not to_attach and not to_detach:
        return
    try:
        for note_id in to_attach:
            attach_note(note_id)
        for note_id in to_detach:
            detach_note(note_id)
        if success_message:
            st.success(success_message)
        st.rerun()
    except Exception as exc:  # pragma: no cover - UI feedback
        st.error(error_message_template.format(exc=exc))


def _render_note_creator(
    *,
    container: Any,
    key: str,
    popover_label: str,
    create_button_label: str,
    empty_warning: str,
    success_message: Optional[str],
    error_message_template: str,
    create_note: CreateNoteFn,
    attach_note: AttachNoteFn,
) -> None:
    with container.popover(popover_label, use_container_width=True):
        new_note_title = st.text_input("Title", key=f"{key}_title")
        new_note_body = st.text_area("Body", key=f"{key}_body", height=160)
        if st.button(
            create_button_label,
            key=f"{key}_create",
            use_container_width=True,
        ):
            body_value = (new_note_body or "").strip()
            if not body_value:
                st.warning(empty_warning)
                return
            try:
                note_id = create_note((new_note_title or "").strip() or None, body_value)
                attach_note(note_id)
                if success_message:
                    st.success(success_message)
                st.rerun()
            except Exception as exc:  # pragma: no cover - UI feedback
                st.error(error_message_template.format(exc=exc))


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


__all__ = ["render_note_editor", "NoteRecord"]
