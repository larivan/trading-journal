"""Диалоги и вспомогательные функции для управления дневными анализами и их этапами."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

import streamlit as st

from components.chart_editor import (
    chart_editor_value_state_key,
    normalize_editor_rows,
    persist_chart_editor,
)
from components.state_header import render_entity_header
from config import ANALYSIS_STATE_VALUES
from db import (
    add_analysis,
    add_analysis_stage,
    attach_chart_to_analysis_stage,
    attach_note_to_analysis_stage,
    delete_analysis_stage,
    detach_note_from_analysis_stage,
    get_analysis,
    list_notes,
    update_analysis,
    update_analysis_stage,
)

from .defaults import build_analysis_defaults
from .sections import (
    render_plan_section,
    render_pre_stage,
    render_post_stage,
)
from .state import visible_stage_types

DialogCallback = Optional[Callable[[int], None]]


def render_analysis_manager(
    *,
    analysis_id: Optional[int] = None,
    on_created: DialogCallback = None,
    on_close: Optional[Callable[[], None]] = None,
) -> None:
    """Единое окно создания и редактирования дневных анализов."""

    dialog_key = _dialog_key(analysis_id)
    is_new_analysis = analysis_id is None
    analysis: Dict[str, Any] = {}
    analysis_error: Optional[str] = None
    analysis_error_level: Optional[str] = None

    if not is_new_analysis:
        if not analysis_id:
            analysis_error = "Анализ не выбран."
            analysis_error_level = "info"
        else:
            existing = get_analysis(analysis_id)
            if not existing:
                analysis_error = "Анализ не найден."
                analysis_error_level = "error"
            else:
                analysis = existing

    defaults = build_analysis_defaults(None if is_new_analysis else analysis)
    analysis_values = defaults["analysis"]
    stage_defaults = defaults["stages"]
    plan_entries = _ensure_plan_entries(dialog_key, defaults["plans"])
    removed_plan_ids_key = _removed_plan_ids_key(dialog_key)
    removed_plan_ids = st.session_state.setdefault(removed_plan_ids_key, [])

    def _format_title(data: Dict[str, Any]) -> str:
        asset_value = (data.get("asset") or "Analysis").strip() or "Analysis"
        date_value = (data.get("date_local") or "—").strip() or "—"
        return f"{asset_value} · {date_value}"

    dialog_title = "New analysis" if is_new_analysis else _format_title(analysis_values)
    all_notes = list_notes()

    @st.dialog(dialog_title, width="large")
    def _dialog() -> None:
        if analysis_error:
            status_fn = st.info if analysis_error_level == "info" else st.error
            status_fn(analysis_error)
            return

        submit_key = f"analysis_submit_{dialog_key}"

        def _submit() -> None:
            st.session_state[submit_key] = True

        def _cancel() -> None:
            _reset_dialog_state(dialog_key)
            if on_close:
                on_close()

        current_stage = (
            analysis.get("state")
            or analysis_values.get("state")
            or ANALYSIS_STATE_VALUES[0]
        )
        status_key = f"analysis_status_{dialog_key}"
        selected_stage = render_entity_header(
            status_label="Текущий этап",
            status_options=ANALYSIS_STATE_VALUES,
            current_status=current_stage,
            status_key=status_key,
            actions=[
                {
                    "label": "Save",
                    "type": "primary",
                    "key": f"analysis_header_save_{dialog_key}",
                    "on_click": _submit,
                },
                {
                    "label": "Cancel",
                    "type": "secondary",
                    "key": f"analysis_header_cancel_{dialog_key}",
                    "on_click": _cancel,
                    "disabled": on_close is None,
                },
            ],
        ) or current_stage

        visible_types = visible_stage_types(selected_stage)

        pre_form: Optional[Dict[str, Any]] = None
        post_form: Optional[Dict[str, Any]] = None
        plan_forms: List[Dict[str, Any]] = []

        for stage_type in ANALYSIS_STATE_VALUES:
            render_stage = stage_type in visible_types
            expanded = stage_type == selected_stage
            if stage_type == "plan":
                plan_forms = render_plan_section(
                    plan_entries=plan_entries,
                    key_prefix=dialog_key,
                    visible=render_stage,
                    expanded=expanded,
                    on_add=lambda key=dialog_key: _add_plan_entry(key),
                    on_remove=lambda entry, key=dialog_key: _remove_plan_entry(
                        key, entry
                    ),
                )
            elif stage_type == "pre-market":
                pre_form = render_pre_stage(
                    stage_key=f"{dialog_key}_pre",
                    stage_data=stage_defaults.get("pre-market"),
                    analysis_defaults=analysis_values,
                    visible=render_stage,
                    expanded=expanded,
                )
            elif stage_type == "post-market":
                post_form = render_post_stage(
                    stage_key=f"{dialog_key}_post",
                    stage_data=stage_defaults.get("post-market"),
                    defaults=analysis_values,
                    visible=render_stage,
                    expanded=expanded,
                    all_notes=all_notes,
                    note_state_key=_post_notes_state_key(dialog_key),
                )

        submitted = st.session_state.pop(submit_key, False)
        if not submitted:
            return

        forms_to_save: List[Dict[str, Any]] = []
        if pre_form:
            forms_to_save.append(pre_form)
        if post_form:
            forms_to_save.append(post_form)
        forms_to_save.extend(plan_forms)

        analysis_payload = _build_analysis_payload(
            base_values=analysis_values,
            selected_stage=selected_stage,
            forms=forms_to_save,
        )

        try:
            current_analysis_id = analysis.get("id")
            if current_analysis_id:
                update_analysis(current_analysis_id, analysis_payload)
            else:
                current_analysis_id = add_analysis(analysis_payload)

            _persist_stage_forms(
                analysis_id=current_analysis_id,
                stage_forms=forms_to_save,
                removed_plan_ids=removed_plan_ids,
            )
            _reset_dialog_state(dialog_key)

            if is_new_analysis:
                if on_created:
                    on_created(current_analysis_id)
                else:
                    st.rerun()
            else:
                st.rerun()
        except Exception as exc:  # pragma: no cover
            st.error(f"Не удалось сохранить анализ: {exc}")

    _dialog()


def _build_analysis_payload(
    *,
    base_values: Dict[str, Any],
    selected_stage: str,
    forms: List[Dict[str, Any]],
) -> Dict[str, Any]:
    payload = {
        "date_local": base_values.get("date_local"),
        "asset": base_values.get("asset"),
        "state": selected_stage,
        "daily_bias": base_values.get("daily_bias"),
        "fact_bias": base_values.get("fact_bias"),
        "day_result": base_values.get("day_result"),
    }
    for form in forms:
        updates = form.get("analysis_updates")
        if updates:
            payload.update(updates)
    return payload


def _persist_stage_forms(
    *,
    analysis_id: int,
    stage_forms: List[Dict[str, Any]],
    removed_plan_ids: List[int],
) -> None:
    for stage_id in {sid for sid in removed_plan_ids if sid}:
        delete_analysis_stage(stage_id)

    for form in stage_forms:
        stage_type = form.get("stage_type")
        if not stage_type:
            continue
        stage_id = form.get("stage_id")
        stage_payload = {
            "analysis_id": analysis_id,
            "type": stage_type,
            "summary": (form.get("summary") or "").strip() or None,
            "time_local": datetime.now().strftime("%H:%M:%S"),
        }
        if stage_id:
            update_analysis_stage(stage_id, stage_payload)
        else:
            stage_id = add_analysis_stage(stage_payload)

        _persist_stage_charts(stage_id, form.get("charts"))
        if stage_type == "post-market":
            _persist_stage_notes(stage_id, form.get("notes"))


def _persist_stage_charts(stage_id: int, charts_info: Optional[Dict[str, Any]]) -> None:
    if not charts_info:
        return
    chart_state_payload = charts_info.get("editor_value")
    if chart_state_payload is None:
        chart_state_payload = charts_info.get("rows_source")
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


def _persist_stage_notes(stage_id: int, notes_info: Optional[Dict[str, Any]]) -> None:
    if not notes_info:
        return
    selected = set(notes_info.get("selected_ids") or [])
    original = set(notes_info.get("original_ids") or [])
    to_attach = selected - original
    to_detach = original - selected
    for note_id in to_attach:
        attach_note_to_analysis_stage(stage_id, note_id)
    for note_id in to_detach:
        detach_note_from_analysis_stage(stage_id, note_id)


def _dialog_key(analysis_id: Optional[int]) -> str:
    return "analysis_create" if analysis_id is None else f"analysis_edit_{analysis_id}"


def _plan_entries_key(dialog_key: str) -> str:
    return f"{dialog_key}_plan_entries"


def _removed_plan_ids_key(dialog_key: str) -> str:
    return f"{dialog_key}_removed_plan_ids"


def _post_notes_state_key(dialog_key: str) -> str:
    return f"{dialog_key}_post_notes"


def _ensure_plan_entries(
    dialog_key: str,
    defaults: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    key = _plan_entries_key(dialog_key)
    if key not in st.session_state:
        if defaults:
            st.session_state[key] = [_plan_entry_from_defaults(dialog_key, item) for item in defaults]
        else:
            st.session_state[key] = [_empty_plan_entry(dialog_key)]
    entries = st.session_state[key]
    if not entries:
        entries.append(_empty_plan_entry(dialog_key))
    return entries


def _plan_entry_from_defaults(dialog_key: str, entry: Dict[str, Any]) -> Dict[str, Any]:
    stage_id = entry.get("stage_id")
    return {
        "key": str(stage_id or uuid4().hex),
        "stage_id": stage_id,
        "summary": entry.get("summary") or "",
        "charts": entry.get("charts") or [],
        "rows_source": entry.get("rows_source"),
        "time_local": entry.get("time_local"),
    }


def _empty_plan_entry(dialog_key: str) -> Dict[str, Any]:
    return {
        "key": uuid4().hex,
        "stage_id": None,
        "summary": "",
        "charts": [],
        "rows_source": None,
        "time_local": None,
    }


def _add_plan_entry(dialog_key: str) -> None:
    entries = st.session_state.setdefault(_plan_entries_key(dialog_key), [])
    entries.append(_empty_plan_entry(dialog_key))
    st.session_state[_plan_entries_key(dialog_key)] = entries
    st.rerun()


def _remove_plan_entry(dialog_key: str, entry: Optional[Dict[str, Any]]) -> None:
    if not entry:
        return
    entries = st.session_state.get(_plan_entries_key(dialog_key), [])
    stage_id = entry.get("stage_id")
    if stage_id:
        removed_ids = st.session_state.setdefault(_removed_plan_ids_key(dialog_key), [])
        if stage_id not in removed_ids:
            removed_ids.append(stage_id)
    entries = [item for item in entries if item["key"] != entry["key"]]
    if not entries:
        entries.append(_empty_plan_entry(dialog_key))
    st.session_state[_plan_entries_key(dialog_key)] = entries
    _cleanup_plan_entry_state(dialog_key, entry["key"])
    st.rerun()


def _cleanup_plan_entry_state(dialog_key: str, entry_key: str) -> None:
    summary_key = f"{dialog_key}_plan_summary_{entry_key}"
    st.session_state.pop(summary_key, None)
    chart_key = f"plan_chart_editor_{dialog_key}_{entry_key}"
    st.session_state.pop(chart_editor_value_state_key(chart_key), None)


def _reset_dialog_state(dialog_key: str) -> None:
    entries_key = _plan_entries_key(dialog_key)
    entries = st.session_state.pop(entries_key, [])
    for entry in entries:
        _cleanup_plan_entry_state(dialog_key, entry["key"])
    st.session_state.pop(_removed_plan_ids_key(dialog_key), None)
    st.session_state.pop(_post_notes_state_key(dialog_key), None)


__all__ = ["render_analysis_manager"]
