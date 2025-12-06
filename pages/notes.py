from datetime import date
from typing import Any, Dict, List, Optional
import streamlit as st
from components.entity_table import render_entity_table
from components.note_manager import render_note_manager
from db import delete_note, list_notes
from helpers import apply_page_config_from_file, format_local_date, format_local_time
from utils.session_state import open_dialog
from config import (
    NOTE_DIALOG_NAME,
    NOTE_ID_STATE,
)


apply_page_config_from_file(__file__)

# === Верхняя панель фильтров ===
search_col, period_col, _, actions_col = st.columns(
    [0.3, 0.2, 0.3, 0.2], vertical_alignment="bottom"
)

with search_col:
    query = st.text_input(
        "Search",
        value="",
        key="notes_search_query",
        placeholder="Type to search…",
    ).strip()

with period_col:
    raw_range = st.date_input(
        "Period",
        value=None,
        key="notes_period",
        format="DD.MM.YYYY",
    )

with actions_col:
    if st.button("Create", type="primary", width="stretch"):
        st.session_state.pop(NOTE_ID_STATE, None)
        open_dialog(NOTE_DIALOG_NAME)

# === Фильтры ===
filters: Dict[str, Any] = {}

if isinstance(raw_range, (list, tuple)):
    values = list(raw_range)
    if len(values) >= 2:
        start, end = values[:2]
        if isinstance(start, date):
            filters["date_from"] = start.isoformat()
        if isinstance(end, date):
            filters["date_to"] = end.isoformat()
elif isinstance(raw_range, date):
    filters["date_from"] = raw_range.isoformat()
    filters["date_to"] = raw_range.isoformat()

if query:
    filters["query"] = query

rows = list_notes(
    filters,
    order_by="date_local",
    ascending=False,
)


def _excerpt(value: Optional[str], limit: int = 120) -> str:
    if not value:
        return ""
    text = value.strip()
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


note_columns: List[Dict[str, Any]] = [
    {
        "field": "date_local",
        "label": "Date",
        "compute": lambda row: row.get("date_local"),
        "format": format_local_date,
        "id": "date_local",
    },
    {
        "field": "time_local",
        "label": "Time",
        "id": "time_local",
        "format": format_local_time,
    },
    {"field": "title", "label": "Title", "id": "title"},
    {
        "field": "body_plain",
        "label": "Preview",
        "compute": lambda row: _excerpt(row.get("body_plain")),
        "id": "preview",
    },
]


def _open_note(row: Dict[str, Any]) -> None:
    note_id = row.get("id")
    if not note_id:
        return
    st.session_state[NOTE_ID_STATE] = note_id
    open_dialog(NOTE_DIALOG_NAME)


def _delete_notes(ids: List[Any]) -> None:
    if not ids:
        return
    for note_id in ids:
        try:
            delete_note(int(note_id))
        except Exception as exc:
            st.toast(f"Failed to delete note #{note_id}: {exc}", icon="❌")
    st.rerun()


table_key = "notes_table"
render_entity_table(
    entity_name="note",
    key=table_key,
    rows=rows,
    columns=note_columns,
    empty_message="Нет заметок.",
    page_size=100,
    on_open=_open_note,
    on_delete=_delete_notes,
)

render_note_manager()
