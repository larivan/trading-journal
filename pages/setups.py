import sqlite3
from typing import Any, Dict, List

import streamlit as st

from components.entity_gallery import render_entity_gallery
from components.setup_manager import render_setup_manager
from config import SETUP_DIALOG_NAME, SETUP_ID_STATE
from db import delete_setup, list_setups
from helpers import apply_page_config_from_file, get_excerpt
from utils.session_state import open_dialog


apply_page_config_from_file(__file__)

search_col, _, actions_col = st.columns(
    [0.6, 0.2, 0.2], vertical_alignment="bottom"
)

with search_col:
    query = st.text_input(
        "Search",
        value="",
        key="setups_search_query",
        placeholder="Type to search...",
    ).strip()

with actions_col:
    if st.button("Create", type="primary", width="stretch"):
        st.session_state.pop(SETUP_ID_STATE, None)
        open_dialog(SETUP_DIALOG_NAME)

filters: Dict[str, Any] = {}
if query:
    filters["query"] = query

rows = list_setups(filters, order_by="name", ascending=True)

setup_columns: List[Dict[str, Any]] = [
    {
        "field": "name",
        "label": "Setup",
        "id": "name",
        "role": "title",
    },
    {
        "field": "description",
        "label": "Description",
        "id": "description",
        "role": "text",
        "format": lambda value: get_excerpt(value, 140),
    },
]


def _open_setup(row: Dict[str, Any]) -> None:
    setup_id = row.get("id")
    if setup_id is None:
        return
    st.session_state[SETUP_ID_STATE] = setup_id
    open_dialog(SETUP_DIALOG_NAME)


def _delete_setups(ids: List[Any]) -> None:
    if not ids:
        return
    for setup_id in ids:
        try:
            delete_setup(int(setup_id))
        except (ValueError, sqlite3.Error) as exc:
            st.toast(f"Failed to delete setup #{setup_id}: {exc}", icon="❌")
    st.rerun()


gallery_key = "setups_gallery"
render_entity_gallery(
    entity_name="setup",
    key=gallery_key,
    rows=rows,
    columns=setup_columns,
    empty_message="No setups yet.",
    page_size=12,
    on_open=_open_setup,
    on_delete=_delete_setups,
)

render_setup_manager()
