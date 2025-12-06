"""Диалог редактирования дневных анализов."""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List
import streamlit as st
from .defaults import build_analysis_defaults
from components.chart_editor import persist_chart_editor
from components.trade_manager import render_trade_manager
from components.note_selector import clear_note_selector_state
from utils.session_state import close_dialog, dialog_is_active
from config import (
    ANALYSIS_DIALOG_NAME,
    ANALYSIS_ID_STATE,
    ANALYSIS_SUCCESS_STATE,
    ANALYSIS_MANAGER_KEY_PREFIX,
    ANALYSIS_STATE_VALUES,
)
from db import (
    add_analysis,
    add_analysis_stage,
    attach_chart_to_analysis_stage,
    attach_note_to_analysis_stage,
    delete_analysis_stage,
    get_analysis,
    transaction,
    update_analysis,
    update_analysis_stage,
    detach_note_from_analysis_stage,
)
from .sections import (
    render_execution_stage,
    render_plan_section,
    render_post_stage,
    render_pre_stage,
)


def render_analysis_manager() -> None:
    """Единое окно создания и редактирования дневных анализов."""
    if "am_success_message" in st.session_state:
        st.toast(st.session_state.pop("am_success_message"), icon="🔥")

    if not dialog_is_active(ANALYSIS_DIALOG_NAME):
        render_trade_manager()
        return

    analysis_id = None
    is_new_analysis = True
    if ANALYSIS_ID_STATE in st.session_state:
        is_new_analysis = False
        analysis_id = st.session_state.get(ANALYSIS_ID_STATE)

    state_key = f"{ANALYSIS_MANAGER_KEY_PREFIX}{analysis_id or 'new'}"

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

    @st.dialog(
        _get_dialog_title(analysis, is_new_analysis),
        width="large",
        on_dismiss=_handle_dialog_dismiss,
    )
    def _dialog() -> None:
        with st.container(border=True):
            status_col, message_col, actions_col = st.columns(
                [0.2, 0.6, 0.2],
                gap="large",
                vertical_alignment="bottom",
            )
            with status_col:
                current_stage = analysis.get(
                    "state") or ANALYSIS_STATE_VALUES[0]
                selected_stage = st.selectbox(
                    "Analysis stage",
                    ANALYSIS_STATE_VALUES,
                    index=(
                        ANALYSIS_STATE_VALUES.index(current_stage)
                        if current_stage
                        else 0
                    ),
                )

            with actions_col:
                submitted = st.button("Save", type="primary", width="stretch")

        visible = _visible_stage_types(selected_stage)

        pre_analysis_values, pre_values = render_pre_stage(
            stage_data=defaults["stages"].get("pre-market"),
            analysis_defaults=defaults["analysis"],
            visible="pre-market" in visible,
            expanded=(selected_stage == "pre-market"),
            state_key=f"{state_key}_pre",
        )

        plan_forms, removed_plan_ids = render_plan_section(
            plan_entries=defaults["plans"],
            visible="plan" in visible,
            expanded=(selected_stage == "plan"),
            state_key=f"{state_key}_plan",
        )

        render_execution_stage(
            analysis_id=analysis_id,
            visible="execution" in visible,
            expanded=(selected_stage == "execution"),
            state_key=f"{state_key}_execution",
        )

        post_analysis_values, post_values = render_post_stage(
            stage_data=defaults["stages"].get("post-market"),
            defaults=defaults["analysis"],
            visible="post-market" in visible,
            expanded=(selected_stage == "post-market"),
            state_key=f"{state_key}_post",
        )

        if not submitted:
            return

        analysis_payload: Dict[str, Any] = {"state": selected_stage}
        if pre_analysis_values:
            analysis_payload.update(pre_analysis_values)
        if post_analysis_values:
            analysis_payload.update(post_analysis_values)

        current_analysis_id = analysis_id
        try:
            with transaction() as conn:
                if is_new_analysis:
                    current_analysis_id = add_analysis(
                        analysis_payload, conn=conn)
                else:
                    update_analysis(current_analysis_id,
                                    analysis_payload, conn=conn)

                if pre_values:
                    pre_stage_id = pre_values["stage_id"]
                    pre_values.update(
                        {
                            "analysis_id": current_analysis_id,
                            "type": "pre-market",
                        }
                    )
                    if pre_stage_id:
                        update_analysis_stage(
                            pre_stage_id, pre_values, conn=conn)
                    else:
                        pre_stage_id = add_analysis_stage(
                            pre_values, conn=conn)

                    persist_chart_editor(
                        attached_charts=pre_values["charts"]["rows_source"],
                        editor_rows=pre_values["charts"]["editor_value"],
                        conn=conn,
                        attach_chart=lambda chart_id, stage_id=pre_stage_id: attach_chart_to_analysis_stage(
                            stage_id, chart_id, conn=conn
                        ),
                    )

                if removed_plan_ids:
                    for stage_id in removed_plan_ids:
                        if not stage_id:
                            continue
                        delete_analysis_stage(stage_id, conn=conn)

                for plan_form in plan_forms:
                    charts_payload = plan_form.get("charts") or {}
                    plan_stage_id = plan_form.get("stage_id")
                    plan_payload = {
                        "analysis_id": current_analysis_id,
                        "type": "plan",
                        "summary": plan_form.get("summary") or "",
                    }
                    if plan_stage_id:
                        update_analysis_stage(
                            plan_stage_id, plan_payload, conn=conn)
                    else:
                        plan_payload["time_local"] = (
                            plan_form.get("time_local") or datetime.now()
                        )
                        plan_stage_id = add_analysis_stage(
                            plan_payload, conn=conn)

                    persist_chart_editor(
                        attached_charts=charts_payload.get(
                            "rows_source") or [],
                        editor_rows=charts_payload.get("editor_value") or [],
                        conn=conn,
                        attach_chart=lambda chart_id, stage_id=plan_stage_id: attach_chart_to_analysis_stage(
                            stage_id, chart_id, conn=conn
                        ),
                    )

                if post_values:
                    post_stage_id = post_values["stage_id"]
                    post_values.update(
                        {
                            "analysis_id": current_analysis_id,
                            "type": "post-market",
                        }
                    )
                    if post_stage_id:
                        update_analysis_stage(
                            post_stage_id, post_values, conn=conn)
                    else:
                        post_values.update({"time_local": datetime.now()})
                        post_stage_id = add_analysis_stage(
                            post_values, conn=conn)

                    persist_chart_editor(
                        attached_charts=post_values["charts"]["rows_source"],
                        editor_rows=post_values["charts"]["editor_value"],
                        conn=conn,
                        attach_chart=lambda chart_id, stage_id=post_stage_id: attach_chart_to_analysis_stage(
                            stage_id, chart_id, conn=conn
                        ),
                    )
                    base_note_ids = {
                        note.get("id")
                        for note in (post_values["notes"]["base_notes"] or [])
                        if note.get("id") is not None
                    }
                    staged_note_ids = {
                        int(nid) for nid in (post_values["notes"]["staged_note_ids"] or []) if nid is not None
                    }
                    for note_id in base_note_ids - staged_note_ids:
                        detach_note_from_analysis_stage(
                            post_stage_id, note_id, conn=conn)
                    for note_id in staged_note_ids - base_note_ids:
                        attach_note_to_analysis_stage(
                            post_stage_id, note_id, conn=conn)

            if is_new_analysis:
                st.session_state[ANALYSIS_ID_STATE] = current_analysis_id
                st.session_state[ANALYSIS_SUCCESS_STATE] = "Analysis created."
            else:
                st.session_state[ANALYSIS_SUCCESS_STATE] = "Analysis saved."
        except Exception as exc:
            message_col.error(f"Failed to save analysis: {exc}")
            return

        st.rerun()

    if dialog_is_active(ANALYSIS_DIALOG_NAME):
        _dialog()


def _get_dialog_title(data: Dict[str, Any], is_new: bool) -> str:
    if is_new:
        return "New analysis"
    if not data:
        return "-"
    asset = (data.get("asset") or "Analysis").strip() or "Analysis"
    date_value = (data.get("date_local") or "—").strip() or "—"
    return f"{asset} · {date_value}"


def _handle_dialog_dismiss() -> None:
    analysis_id = st.session_state.pop(ANALYSIS_ID_STATE, None)
    clear_note_selector_state(
        f"{ANALYSIS_MANAGER_KEY_PREFIX}{analysis_id or 'new'}_post_note_selector"
    )
    close_dialog()


def _visible_stage_types(current_stage: str) -> List[str]:
    """Возвращает последовательность этапов, которые должны отображаться."""

    if current_stage not in ANALYSIS_STATE_VALUES:
        return [ANALYSIS_STATE_VALUES[0]]
    idx = ANALYSIS_STATE_VALUES.index(current_stage)
    return ANALYSIS_STATE_VALUES[: idx + 1]


__all__ = ["render_analysis_manager"]
