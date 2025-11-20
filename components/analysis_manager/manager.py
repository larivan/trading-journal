"""Dialogs and helpers for managing daily analyses и их этапов."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import streamlit as st

from components.chart_editor import normalize_editor_rows, persist_chart_editor
from components.state_header import render_entity_header
from config import ANALYSIS_STATE_VALUES
from db import (
    add_analysis,
    attach_chart_to_analysis_stage,
    delete_analysis,
    get_analysis,
    update_analysis,
    update_analysis_stage,
)

from .defaults import build_analysis_defaults
from .sections import (
    render_plan_section,
    render_pre_stage,
    render_post_stage,
)
from .state import ensure_stage_records, visible_stage_types

DialogCallback = Optional[Callable[[int], None]]


def render_analysis_creator(
    *,
    on_created: DialogCallback = None,
    on_cancel: Optional[Callable[[], None]] = None,
) -> None:
    """Диалог создания анализа."""

    @st.dialog("New analysis", width="small")
    def _dialog() -> None:
        defaults = build_analysis_defaults()
        primary_payload = render_primary_fields(
            form_key="analysis_create",
            defaults=defaults,
        )

        col1, col2 = st.columns(2)
        submitted = col1.button("Create", type="primary",
                                use_container_width=True)
        if not submitted:
            if col2.button("Cancel", use_container_width=True):
                if on_cancel:
                    on_cancel()
            return

        analysis_payload = {
            "date_local": primary_payload["date_local"],
            "asset": primary_payload["asset"],
            "state": ANALYSIS_STATE_VALUES[0],
        }

        try:
            analysis_id = add_analysis(analysis_payload)
            if on_created:
                on_created(analysis_id)
            else:
                st.rerun()
        except Exception as exc:  # pragma: no cover - UI feedback
            st.error(f"Не удалось создать анализ: {exc}")

    _dialog()


def render_analysis_editor(
    *,
    analysis_id: Optional[int],
    on_close: Optional[Callable[[], None]] = None,
) -> None:
    """Редактирование существующего анализа и его этапов."""

    if not analysis_id:
        st.info("Анализ не выбран.")
        return
    analysis = get_analysis(analysis_id)
    if not analysis:
        st.error("Анализ не найден.")
        return

    defaults = build_analysis_defaults(analysis)
    title = f"{defaults['asset']} · {defaults['date_local']}"

    @st.dialog(title, width="large")
    def _dialog() -> None:
        header_container = st.container(border=True)
        with header_container:
            def _submit_primary() -> None:
                st.session_state[f"analysis_submit_{analysis_id}"] = True

            def _cancel_primary() -> None:
                if on_close:
                    on_close()

            current_stage = analysis.get("state") or ANALYSIS_STATE_VALUES[0]
            selected_stage = render_entity_header(
                status_label="Текущий этап",
                status_options=ANALYSIS_STATE_VALUES,
                current_status=current_stage,
                status_key=f"analysis_status_{analysis_id}",
                actions=[
                    {
                        "label": "Save",
                        "type": "primary",
                        "key": f"analysis_header_save_{analysis_id}",
                        "on_click": _submit_primary,
                    },
                    {
                        "label": "Cancel",
                        "type": "secondary",
                        "key": f"analysis_header_cancel_{analysis_id}",
                        "on_click": _cancel_primary,
                        "disabled": on_close is None,
                    },
                ],
            ) or current_stage

        stage_map, plan_stages = ensure_stage_records(analysis_id)
        visible_types = visible_stage_types(selected_stage)

        pre_form: Optional[Dict[str, Any]] = None
        post_form: Optional[Dict[str, Any]] = None
        plan_forms: List[Dict[str, Any]] = []

        for stage_type in ANALYSIS_STATE_VALUES:
            render = stage_type in visible_types
            expanded = stage_type == selected_stage
            if stage_type == "plan":
                plan_forms = render_plan_section(
                    plan_stages=plan_stages,
                    analysis_id=analysis_id,
                    visible=render,
                    expanded=expanded,
                )
            elif stage_type == "pre-market":
                pre_form = render_pre_stage(
                    stage_data=stage_map.get(stage_type),
                    defaults=defaults,
                    visible=render,
                    expanded=expanded,
                )
            elif stage_type == "post-market":
                post_form = render_post_stage(
                    stage_data=stage_map.get(stage_type),
                    defaults=defaults,
                    visible=render,
                    expanded=expanded,
                )

        submitted_primary = st.session_state.pop(
            f"analysis_submit_{analysis_id}", False
        )
        if submitted_primary:
            forms_to_save: List[Dict[str, Any]] = []
            if pre_form:
                forms_to_save.append(pre_form)
            if post_form:
                forms_to_save.append(post_form)
            forms_to_save.extend(plan_forms)

            analysis_updates: Dict[str, Any] = {
                "state": selected_stage,
            }
            for form in forms_to_save:
                updates = form.get("analysis_updates")
                if updates:
                    analysis_updates.update(updates)

            try:
                update_analysis(analysis_id, analysis_updates)
                for form in forms_to_save:
                    _persist_stage_form(analysis_id, form)
                st.success("Изменения сохранены.")
                st.rerun()
            except Exception as exc:  # pragma: no cover
                st.error(f"Не удалось сохранить: {exc}")
    _dialog()


def render_analysis_remover(
    *,
    analysis_id: Optional[int],
    on_cancel: Optional[Callable[[], None]] = None,
    on_deleted: Optional[Callable[[], None]] = None,
) -> None:
    """Диалог удаления анализа."""

    @st.dialog("Удаление анализа")
    def _dialog() -> None:
        if not analysis_id:
            st.warning("Анализ не выбран.")
            if st.button("Закрыть", use_container_width=True):
                if on_cancel:
                    on_cancel()
            return

        st.warning(
            "Анализ будет удалён вместе с этапами, чартами и заметками. Подтвердите действие.",
            icon="⚠️",
        )
        col_ok, col_cancel = st.columns(2)
        if col_ok.button(
            "Удалить",
            type="primary",
            use_container_width=True,
        ):
            try:
                delete_analysis(analysis_id)
                st.success("Анализ удалён.")
                if on_deleted:
                    on_deleted()
                else:
                    st.rerun()
            except Exception as exc:  # pragma: no cover
                st.error(f"Не удалось удалить анализ: {exc}")
        if col_cancel.button("Отмена", use_container_width=True):
            if on_cancel:
                on_cancel()

    _dialog()


def _persist_stage_form(analysis_id: int, form: Optional[Dict[str, Any]]) -> None:
    if not form:
        return
    stage_id = form.get("stage_id")
    stage_type = form.get("stage_type")
    if stage_id is None or not stage_type:
        return

    stage_payload = {
        "analysis_id": analysis_id,
        "type": stage_type,
        "summary": (form.get("summary") or "").strip() or None,
        "time_local": datetime.now().strftime("%H:%M:%S"),
    }
    update_analysis_stage(stage_id, stage_payload)

    charts_info = form.get("charts")
    if not charts_info:
        return
    chart_state_payload = (
        charts_info.get("editor_value")
        if charts_info.get("editor_value") is not None
        else charts_info.get("rows_source")
    )
    if chart_state_payload is None:
        return
    editor_rows = normalize_editor_rows(chart_state_payload)
    persist_chart_editor(
        attached_charts=charts_info.get("attached") or [],
        editor_rows=editor_rows,
        attach_chart=lambda chart_id, s_id=stage_id: attach_chart_to_analysis_stage(
            s_id, chart_id
        ),
    )
