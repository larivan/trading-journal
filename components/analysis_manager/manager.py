"""Диалог редактирования дневных анализов."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import streamlit as st

from components.chart_editor import (
    chart_editor_value_state_key,
    normalize_editor_rows,
    persist_chart_editor,
)
from config import ANALYSIS_STATE_VALUES
from db import (
    add_analysis,
    add_analysis_stage,
    attach_chart_to_analysis_stage,
    delete_analysis_stage,
    get_analysis,
    update_analysis,
    update_analysis_stage,
)
from utils.session_state import close_dialog, dialog_is_active

from .defaults import build_analysis_defaults
from .sections import (
    render_plan_section,
    render_post_stage,
    render_pre_stage,
)
from .state import visible_stage_types

ANALYSIS_DIALOG_NAME = "analysis_manager"
ANALYSIS_ID_STATE = "am_analysis_id"
ANALYSIS_SUCCESS_STATE = "am_success_message"
ANALYSIS_CONTEXT_STATE = "am_active_context"


def render_analysis_manager() -> None:
    """Единое окно создания и редактирования дневных анализов."""
    if "am_success_message" in st.session_state:
        st.toast(st.session_state.pop("am_success_message"), icon="🔥")

    if not dialog_is_active(ANALYSIS_DIALOG_NAME):
        st.session_state.pop(ANALYSIS_CONTEXT_STATE, None)
        return

    analysis_id = None
    is_new_analysis = True
    if ANALYSIS_ID_STATE in st.session_state:
        is_new_analysis = False
        analysis_id = st.session_state.get(ANALYSIS_ID_STATE)

    state_key = f"am_analysis_id_${analysis_id}"

    analysis: Dict[str, Any] = {}
    if not is_new_analysis:
        analysis = get_analysis(analysis_id) or {}
        if not analysis:
            st.error("Analysis not found.")
            st.session_state.pop(ANALYSIS_ID_STATE, None)
            close_dialog()
            st.rerun()
            return

    defaults = build_analysis_defaults(analysis)
    plan_entries = _ensure_plan_entries(defaults["plans"])
    # removed_plan_ids = st.session_state.setdefault(
    #     _removed_plan_ids_key(context_key), []
    # )

    def _handle_dialog_dismiss() -> None:
        # _reset_dialog_state(context_key)
        st.session_state.pop(ANALYSIS_CONTEXT_STATE, None)
        st.session_state.pop(ANALYSIS_ID_STATE, None)
        close_dialog()

    @st.dialog(_get_dialog_title(analysis, is_new_analysis), width="large", on_dismiss=_handle_dialog_dismiss)
    def _dialog() -> None:
        with st.container(border=True):
            status_col, message_col, actions_col = st.columns(
                [0.2, 0.6, 0.2],
                gap="large",
                vertical_alignment="bottom",
            )
            with status_col:
                current_stage = (
                    analysis.get("state")
                    or ANALYSIS_STATE_VALUES[0]
                )
                selected_stage = st.selectbox(
                    "Analysis stage",
                    ANALYSIS_STATE_VALUES,
                    index=ANALYSIS_STATE_VALUES.index(current_stage)
                    if current_stage else 0,
                )

            with actions_col:
                submitted = st.button(
                    "Save",
                    type="primary",
                    width="stretch"
                )

        visible = visible_stage_types(selected_stage)

        pre_analysis_values, pre_values = render_pre_stage(
            stage_data=defaults["stages"].get("pre-market"),
            analysis_defaults=defaults["analysis"],
            visible="pre-market" in visible,
            expanded=(selected_stage == "pre-market"),
            state_key=f"${state_key}_pre"
        )

        # plan_forms = render_plan_section(
        #     plan_entries=plan_entries,
        #     visible="plan" in visible,
        #     expanded=(selected_stage == "plan")
        # )

        post_analysis_values, post_values = render_post_stage(
            stage_data=defaults["stages"].get("post-market"),
            defaults=defaults["analysis"],
            visible="post-market" in visible,
            expanded=(selected_stage == "post-market"),
            state_key=f"${state_key}_post"
        )

        if not submitted:
            return

        analysis_payload: Dict[str, Any] = {"state": selected_stage}
        if pre_analysis_values:
            analysis_payload.update(pre_analysis_values)
        if post_analysis_values:
            analysis_payload.update(post_analysis_values)
        # forms_to_save.extend(plan_forms)

        current_analysis_id = analysis_id
        try:
            if is_new_analysis:
                current_analysis_id = add_analysis(analysis_payload)
                st.session_state[ANALYSIS_ID_STATE] = current_analysis_id
                st.session_state[ANALYSIS_SUCCESS_STATE] = "Analysis created."
            else:
                update_analysis(current_analysis_id, analysis_payload)
                st.session_state[ANALYSIS_SUCCESS_STATE] = "Analysis saved."
        except Exception as exc:
            message_col.error(f"Failed to save analysis: {exc}")
            return

        if (pre_values):
            pre_stage_id = pre_values["stage_id"]
            pre_values.update({
                "analysis_id": current_analysis_id,
                "type": "pre-market",
            })
            try:
                if (pre_stage_id):
                    update_analysis_stage(pre_stage_id, pre_values)
                else:
                    pre_values.update({"time_local": datetime.now()})
                    pre_stage_id = add_analysis_stage(pre_values)
            except Exception as exc:
                message_col.error(f"Failed to save analysis: {exc}")
                return

            try:
                persist_chart_editor(
                    attached_charts=pre_values["charts"]["rows_source"],
                    editor_rows=pre_values["charts"]["editor_value"],
                    attach_chart=lambda chart_id, stage_id=pre_stage_id: attach_chart_to_analysis_stage(
                        stage_id, chart_id
                    ),
                )
            except Exception as exc:
                message_col.error(f"Failed to save charts: {exc}")
                return

        if (post_values):
            post_stage_id = post_values["stage_id"]
            post_values.update({
                "analysis_id": current_analysis_id,
                "type": "post-market",
            })
            try:
                if (post_stage_id):
                    update_analysis_stage(post_stage_id, post_values)
                else:
                    post_values.update({"time_local": datetime.now()})
                    post_stage_id = add_analysis_stage(post_values)
            except Exception as exc:
                message_col.error(f"Failed to save analysis: {exc}")
                return

            try:
                persist_chart_editor(
                    attached_charts=post_values["charts"]["rows_source"],
                    editor_rows=post_values["charts"]["editor_value"],
                    attach_chart=lambda chart_id, stage_id=post_stage_id: attach_chart_to_analysis_stage(
                        stage_id, chart_id
                    ),
                )
            except Exception as exc:
                message_col.error(f"Failed to save charts: {exc}")
                return
        st.rerun()

    if dialog_is_active(ANALYSIS_DIALOG_NAME):
        _dialog()


def _plan_entries_key(context_key: str) -> str:
    return f"{context_key}_plan_entries"


def _removed_plan_ids_key(context_key: str) -> str:
    return f"{context_key}_removed_plan_ids"


def _ensure_plan_entries(
    defaults: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    entries = []
    for item in defaults:
        stage_id = item.get("stage_id")
        entries.append({
            "key": str(stage_id or uuid4().hex),
            "stage_id": stage_id,
            "summary": item.get("summary") or "",
            "charts": item.get("charts") or [],
            "rows_source": item.get("rows_source"),
            "time_local": item.get("time_local"),
        })


def _reset_dialog_state(context_key: str) -> None:
    entries_key = _plan_entries_key(context_key)
    entries = st.session_state.pop(entries_key, [])
    for entry in entries:
        _cleanup_plan_entry_state(context_key, entry["key"])
    st.session_state.pop(_removed_plan_ids_key(context_key), None)


def _get_dialog_title(data: Dict[str, Any], is_new: bool) -> str:
    if is_new:
        return "New analysis"
    if not data:
        return "-"
    asset = (data.get("asset") or "Analysis").strip() or "Analysis"
    date_value = (data.get("date_local") or "—").strip() or "—"
    return f"{asset} · {date_value}"


__all__ = ["render_analysis_manager"]
