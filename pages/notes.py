from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from components.database_toolbar import render_database_toolbar
from components.entity_filters import TAB_DEFINITIONS, ensure_custom_range
from components.entity_table import render_entity_table
from components.note_manager import render_note_manager
from config import NOTE_TYPE_VALUES
from db import delete_note, list_notes
from helpers import apply_page_config_from_file, format_local_date, format_local_time
from utils.session_state import (
    apply_period_filters,
    close_entity_dialog,
    dialog_is_open,
    get_selected_entity,
    init_entity_state,
    open_entity_dialog,
    set_selected_entity,
    switch_to_edit_dialog,
)

apply_page_config_from_file(__file__)

today = date.today()
default_notes_range = (today - timedelta(days=7), today)
init_entity_state(entity_name="note", default_range=default_notes_range)


def _render_notes_custom_filters(
    initial_range: Optional[Tuple[Optional[date], Optional[date]]],
) -> Tuple[Dict[str, Optional[str]], Tuple[Optional[date], Optional[date]]]:
    default_from, default_to = ensure_custom_range(initial_range)

    with st.container():
        fc1, fc2, fc3, _ = st.columns([0.2, 0.2, 0.3, 0.3])
        raw_date_range = fc1.date_input(
            "Диапазон дат",
            value=(default_from, default_to),
            format="DD.MM.YYYY",
        )
        if isinstance(raw_date_range, (list, tuple)):
            range_values = list(raw_date_range)
            while len(range_values) < 2:
                range_values.append(default_to)
            raw_from, raw_to = range_values[:2]
        else:
            raw_from, raw_to = raw_date_range, default_to
        date_from = raw_from if isinstance(raw_from, date) else default_from
        date_to = raw_to if isinstance(raw_to, date) else default_to
        note_type_choice = fc2.selectbox(
            "Тип заметки",
            ["Все"] + list(NOTE_TYPE_VALUES),
        )
        query_value = fc3.text_input(
            "Поиск",
            placeholder="Заголовок или текст",
        )

    filters: Dict[str, Optional[str]] = {}
    if note_type_choice != "Все":
        filters["note_type"] = note_type_choice
    query_clean = (query_value or "").strip()
    if query_clean:
        filters["query"] = query_clean

    return filters, (date_from, date_to)


render_database_toolbar(
    tab_definitions=TAB_DEFINITIONS,
    session_prefix="notes",
    entity_name="note",
)
tab_filters, date_from, date_to, selected_tab_key = apply_period_filters(
    entity_name="note",
    session_prefix="notes",
    default_range=default_notes_range,
    tab_definitions=TAB_DEFINITIONS,
    render_custom_filters=_render_notes_custom_filters,
)


rows = list_notes(
    tab_filters,
    order_by="date_local",
    ascending=False,
)


def _body_preview(row: Dict[str, Any]) -> str:
    text = (row.get("body") or "").strip()
    if len(text) > 100:
        return text[:97].rstrip() + "..."
    return text


note_columns: List[Dict[str, Any]] = [
    {
        "field": "date_local",
        "label": "Дата",
        "compute": lambda row: row.get("date_local"),
        "format": format_local_date,
        "id": "date_local",
    },
    {
        "field": "time_local",
        "label": "Время",
        "compute": lambda row: row.get("time_local"),
        "format": format_local_time,
        "id": "time_local",
    },
    {"field": "title", "label": "Заголовок", "id": "title"},
    {"field": "note_type", "label": "Тип", "id": "note_type"},
    {
        "field": "body",
        "label": "Текст",
        "compute": _body_preview,
        "id": "body",
    },
]


def _handle_open_note(row: Dict[str, Any]) -> None:
    note_id = row.get("id")
    if not note_id:
        return
    set_selected_entity("note", note_id)
    open_entity_dialog("note", "edit")


def _delete_note_and_refresh(note_id: Optional[int]) -> None:
    if not note_id:
        return
    try:
        delete_note(note_id)
        set_selected_entity("note", None)
        st.rerun()
    except Exception as exc:
        st.error(f"Не удалось удалить заметку: {exc}")


def _handle_delete_notes(ids: List[Any]) -> None:
    if not ids:
        return
    _delete_note_and_refresh(ids[0])


table_key = f"notes_table_{selected_tab_key}"
render_entity_table(
    entity_name="note",
    key=table_key,
    rows=rows,
    columns=note_columns,
    empty_message="Нет заметок для выбранного периода.",
    page_size=100,
    on_open=_handle_open_note,
    on_delete=_handle_delete_notes,
)


def _handle_note_created(new_note_id: int) -> None:
    switch_to_edit_dialog("note", new_note_id)


def _close_edit_dialog() -> None:
    close_entity_dialog("note", "edit")


def _close_create_dialog() -> None:
    close_entity_dialog("note", "create")


if dialog_is_open("note", "create"):
    render_note_manager(
        note_id=None,
        on_created=_handle_note_created,
        on_close=_close_create_dialog,
    )
if dialog_is_open("note", "edit"):
    render_note_manager(
        note_id=get_selected_entity("note"),
        on_close=_close_edit_dialog,
    )
