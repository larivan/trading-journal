"""Dialog for creating and editing setups."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List

import streamlit as st

from components.chart_editor import (
    chart_table_rows,
    persist_chart_editor,
    render_chart_editor,
)
from config import (
    SETUP_DIALOG_NAME,
    SETUP_ID_STATE,
    SETUP_MANAGER_KEY_PREFIX,
    SETUP_SUCCESS_STATE,
)
from db import (
    attach_chart_to_setup,
    create_setup,
    delete_setup,
    get_setup,
    list_charts,
    transaction,
    update_setup,
)
from utils.session_state import close_dialog, dialog_is_active


def render_setup_manager() -> None:
    """Render the setup create/edit dialog."""
    if SETUP_SUCCESS_STATE in st.session_state:
        st.toast(st.session_state.pop(SETUP_SUCCESS_STATE))

    if not dialog_is_active(SETUP_DIALOG_NAME):
        return

    setup_id = st.session_state.get(SETUP_ID_STATE)
    is_new = setup_id is None
    setup: Dict[str, Any] = {}

    if not is_new:
        setup = get_setup(int(setup_id)) or {}
        if not setup:
            st.error("Setup not found.")
            _reset_setup_state()
            close_dialog()
            st.rerun()
            return

    state_key = f"{SETUP_MANAGER_KEY_PREFIX}{setup_id or 'new'}"
    charts: List[Dict[str, Any]] = list_charts(
        setup_id=setup_id) if setup_id else []

    @st.dialog(
        _get_dialog_title(setup, is_new),
        width="medium",
        on_dismiss=_handle_dialog_dismiss,
    )
    def _dialog() -> None:
        name_value = st.text_input(
            "Name",
            value=setup.get("name") or "",
            key=f"{state_key}_name",
            placeholder="Setup name",
        )
        st.markdown("#### Charts")
        chart_values = render_chart_editor(
            key=f"{state_key}_charts",
            base_rows=chart_table_rows(charts),
            layout_columns=2,
        )
        description_value = st.text_area(
            "Description",
            value=setup.get("description") or "",
            height=200,
            key=f"{state_key}_description",
            placeholder="Optional",
        )

        st.divider()

        c1, c2 = st.columns(2)
        save_clicked = c1.button(
            "Save",
            type="primary",
            width="stretch",
            key=f"{state_key}_save",
        )
        delete_clicked = c2.button(
            "Delete",
            type="secondary",
            width="stretch",
            key=f"{state_key}_delete",
            disabled=is_new,
        )

        if delete_clicked and not is_new:
            try:
                delete_setup(int(setup_id))
            except (ValueError, sqlite3.Error) as exc:
                st.error(f"Failed to delete setup: {exc}")
                return
            _reset_setup_state()
            st.session_state[SETUP_SUCCESS_STATE] = "Setup deleted."
            close_dialog()
            st.rerun()

        if save_clicked:
            name_clean = (name_value or "").strip()
            if not name_clean:
                st.error("Provide the setup name.")
                return

            payload: Dict[str, Any] = {
                "name": name_clean,
                "description": (description_value or "").strip() or None,
            }

            try:
                with transaction() as conn:
                    current_setup_id = setup_id
                    setup_charts = charts or []
                    if is_new:
                        current_setup_id = create_setup(
                            payload["name"],
                            payload["description"],
                            conn=conn,
                        )
                    else:
                        update_setup(int(setup_id), payload, conn=conn)

                    persist_chart_editor(
                        attached_charts=setup_charts,
                        editor_rows=chart_values,
                        conn=conn,
                        attach_chart=lambda chart_id, setup_id=current_setup_id: attach_chart_to_setup(  # noqa: E731
                            setup_id, chart_id, conn=conn
                        ),
                    )

                if is_new:
                    st.session_state[SETUP_ID_STATE] = current_setup_id
                    st.session_state[SETUP_SUCCESS_STATE] = "Setup created."
                else:
                    st.session_state[SETUP_SUCCESS_STATE] = "Setup saved."
            except (ValueError, sqlite3.Error) as exc:
                st.error(f"Failed to save setup: {exc}")
                return

            st.rerun()

    if dialog_is_active(SETUP_DIALOG_NAME):
        _dialog()


def _get_dialog_title(data: Dict[str, Any], is_new: bool) -> str:
    if is_new:
        return "New setup"
    return (data.get("name") or "Setup").strip()


def _handle_dialog_dismiss() -> None:
    _reset_setup_state()
    close_dialog()


def _reset_setup_state() -> None:
    st.session_state.pop(SETUP_ID_STATE, None)


__all__ = ["render_setup_manager"]
