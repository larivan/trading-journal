import sqlite3
from datetime import date
from typing import Any, Dict, List
import streamlit as st
from components.entity_gallery import render_entity_gallery
from components.note_manager import render_note_manager
from db import delete_note, count_notes_by_trade, count_notes_by_analysis
from utils.cached_data import cached_notes, filter_notes
from helpers import (
    format_local_date,
    format_local_time,
    get_excerpt
)
from utils.session_state import open_dialog
from utils.auth import get_current_user_id
from config import (
    NOTE_DIALOG_NAME,
    NOTE_ID_STATE,
)

st.set_page_config(page_title="Notes", page_icon=":material/sticky_note_2:", layout="wide")
st.title(":material/sticky_note_2: Notes")

user_id = get_current_user_id()

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
    date_range = st.date_input(
        "Date",
        value=[],
        key="notes_period",
        format="DD.MM.YYYY",
    )

with actions_col:
    if st.button("Create", type="primary", width="stretch"):
        st.session_state.pop(NOTE_ID_STATE, None)
        open_dialog(NOTE_DIALOG_NAME)

# === Фильтры ===
filters: Dict[str, Any] = {}

if date_range:
    if len(date_range) < 2:
        date_range = (date_range[0], date.today())
    filters["date_from"] = date_range[0].isoformat()
    filters["date_to"] = date_range[1].isoformat()

if query:
    filters["query"] = query

rows = filter_notes(
    cached_notes(user_id),
    filters,
    order_by="date_local",
    ascending=False,
)

notes_by_trade = count_notes_by_trade(user_id)
notes_by_analysis = count_notes_by_analysis(user_id)

note_columns: List[Dict[str, Any]] = [
    {
        "field": "category",
        "label": "Category",
        "id": "category",
        "role": "detail",
    },
    {
        "field": "date_local",
        "label": "Date",
        "compute": lambda row: row.get("date_local"),
        "format": format_local_date,
        "id": "date_local",
        "role": "detail"
    },
    {
        "field": "time_local",
        "label": "Time",
        "id": "time_local",
        "format": format_local_time,
        "role": "hidden"
    },
    {
        "field": "excerpt",
        "label": "Excerpt",
        "compute": lambda row: get_excerpt(row.get("body"), 60),
        "id": "excerpt",
        "role": "text"
    },
    {
        "field": "linked",
        "label": "Linked",
        "compute": lambda row: _linked_label(row.get("id"), notes_by_trade, notes_by_analysis),
        "id": "linked",
        "role": "detail",
    },
]


def _linked_label(
    note_id: Any,
    by_trade: Dict[int, int],
    by_analysis: Dict[int, int],
) -> str:
    if not note_id:
        return ""
    t = by_trade.get(int(note_id), 0)
    a = by_analysis.get(int(note_id), 0)
    if t and a:
        return f"🔗 {t} trade{'s' if t != 1 else ''} · {a} anal{'yses' if a != 1 else 'ysis'}"
    if t:
        return f"🔗 {t} trade{'s' if t != 1 else ''}"
    if a:
        return f"🔗 {a} anal{'yses' if a != 1 else 'ysis'}"
    return ""


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
            delete_note(int(note_id), user_id)
        except (ValueError, sqlite3.Error) as exc:
            st.toast(f"Failed to delete note #{note_id}: {exc}", icon="❌")
    cached_notes.clear()
    st.rerun()


table_key = "notes_table"
render_entity_gallery(
    entity_name="note",
    key=table_key,
    rows=rows,
    columns=note_columns,
    empty_message="No notes found.",
    page_size=30,
    on_open=_open_note,
    on_delete=_delete_notes,
)

render_note_manager()
