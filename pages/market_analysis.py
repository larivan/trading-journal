from datetime import date, timedelta

import streamlit as st

from components.analysis_creator import render_analysis_creator_dialog
from components.analysis_filters import (
    TAB_DEFINITIONS,
    build_analysis_filters,
    tab_date_range,
)
from components.analysis_manager import render_analysis_manager_dialog
from components.analysis_remover import render_analysis_remove_dialog
from components.analysis_table import render_analysis_table
from components.database_toolbar import (
    render_action_buttons,
    render_database_toolbar,
)
from db import list_analysis
from helpers import apply_page_config_from_file

apply_page_config_from_file(__file__)

today = date.today()
st.session_state.setdefault("analysis_active_filters", {})
st.session_state.setdefault(
    "analysis_custom_range",
    (
        today - timedelta(days=7),
        today,
    ),
)

st.session_state.setdefault("selected_analysis_id", None)
st.session_state.setdefault("show_analysis_create", False)
st.session_state.setdefault("show_analysis_edit", False)
st.session_state.setdefault("show_analysis_delete", False)


def _set_flag(flag: str, value: bool) -> None:
    st.session_state[flag] = value


selected_label, selected_tab_key, tab_changed, actions_placeholder = render_database_toolbar(
    tab_definitions=TAB_DEFINITIONS,
    session_prefix="analysis",
)

if tab_changed:
    st.session_state["selected_analysis_id"] = None
    _set_flag("show_analysis_create", False)
    _set_flag("show_analysis_edit", False)
    _set_flag("show_analysis_delete", False)
    table_state_key = f"analysis_table_{selected_tab_key}"
    st.session_state.pop(table_state_key, None)
    st.session_state.pop(f"{table_state_key}_selection", None)
st.session_state["analysis_visible_tab"] = selected_tab_key
st.session_state["analysis_active_period"] = selected_label

if selected_tab_key == "custom":
    filters, custom_range = build_analysis_filters(
        st.session_state.get("analysis_active_filters"),
        st.session_state.get("analysis_custom_range"),
    )
    st.session_state["analysis_active_filters"] = filters
    st.session_state["analysis_custom_range"] = custom_range
    tab_filters = filters.copy()
    date_from, date_to = custom_range
else:
    tab_filters = st.session_state.get("analysis_active_filters", {}).copy()
    date_from, date_to = tab_date_range(selected_tab_key)
if date_from:
    tab_filters["date_from"] = date_from.isoformat()
if date_to:
    tab_filters["date_to"] = date_to.isoformat()


rows = list_analysis(tab_filters)
selection_changed, selected_from_tab = render_analysis_table(
    rows,
    selected_tab_key,
)
if selection_changed:
    if selected_from_tab is None:
        if not st.session_state.get("show_analysis_edit"):
            st.session_state["selected_analysis_id"] = None
            _set_flag("show_analysis_create", False)
            _set_flag("show_analysis_edit", False)
            _set_flag("show_analysis_delete", False)
    else:
        st.session_state["selected_analysis_id"] = selected_from_tab
        _set_flag("show_analysis_create", False)
        _set_flag("show_analysis_edit", False)
        _set_flag("show_analysis_delete", False)


open_disabled = st.session_state.get("selected_analysis_id") is None
create_clicked, open_clicked, delete_clicked = render_action_buttons(
    actions_container=actions_placeholder,
    session_prefix="analysis",
    open_disabled=open_disabled,
)

if create_clicked:
    _set_flag("show_analysis_create", True)
    _set_flag("show_analysis_edit", False)
    _set_flag("show_analysis_delete", False)
if open_clicked:
    _set_flag("show_analysis_edit", True)
    _set_flag("show_analysis_create", False)
    _set_flag("show_analysis_delete", False)
if delete_clicked:
    _set_flag("show_analysis_delete", True)
    _set_flag("show_analysis_create", False)
    _set_flag("show_analysis_edit", False)


def _close_create_dialog() -> None:
    _set_flag("show_analysis_create", False)
    st.rerun()


def _handle_analysis_created(new_analysis_id: int) -> None:
    st.session_state["selected_analysis_id"] = new_analysis_id
    _set_flag("show_analysis_create", False)
    _set_flag("show_analysis_edit", True)
    st.rerun()


def _close_edit_dialog() -> None:
    _set_flag("show_analysis_edit", False)
    st.rerun()


def _handle_analysis_saved() -> None:
    _set_flag("show_analysis_edit", False)
    st.rerun()


def _close_delete_dialog() -> None:
    _set_flag("show_analysis_delete", False)
    st.rerun()


def _handle_analysis_deleted() -> None:
    st.session_state["selected_analysis_id"] = None
    _set_flag("show_analysis_delete", False)
    st.rerun()


if st.session_state.get("show_analysis_create"):
    render_analysis_creator_dialog(
        on_created=_handle_analysis_created,
        on_cancel=_close_create_dialog,
    )
if st.session_state.get("show_analysis_edit"):
    render_analysis_manager_dialog(
        analysis_id=st.session_state.get("selected_analysis_id"),
        on_saved=_handle_analysis_saved,
        on_close=_close_edit_dialog,
    )
if st.session_state.get("show_analysis_delete"):
    render_analysis_remove_dialog(
        analysis_id=st.session_state.get("selected_analysis_id"),
        on_deleted=_handle_analysis_deleted,
        on_cancel=_close_delete_dialog,
    )
