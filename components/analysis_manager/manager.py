"""Dialogs and helpers for managing daily analyses and their stages."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional, Set

import streamlit as st

from components.chart_editor import (
    chart_table_rows,
    normalize_editor_rows,
    persist_chart_editor,
    render_chart_editor,
)
from components.state_header import render_entity_header
from config import ANALYSIS_STATE_VALUES, ASSETS, DAILY_BIAS, DAY_RESULT_VALUES
from db import (
    add_analysis,
    add_analysis_stage,
    add_note,
    attach_chart_to_analysis_stage,
    attach_note_to_analysis_stage,
    delete_analysis,
    get_analysis,
    get_analysis_stage,
    list_analysis_stage_charts,
    list_analysis_stage_notes,
    list_analysis_stages,
    list_notes,
    detach_note_from_analysis_stage,
    update_analysis,
    update_analysis_stage,
)

DialogCallback = Optional[Callable[[int], None]]

STAGE_TITLES = {
    "pre-market": "Pre-market",
    "plan": "Plan",
    "post-market": "Post-market",
}


def _analysis_build_defaults(analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    analysis = analysis or {}
    return {
        "date_local": analysis.get("date_local") or date.today().isoformat(),
        "asset": analysis.get("asset") or (ASSETS[0] if ASSETS else ""),
        "state": analysis.get("state") or (ANALYSIS_STATE_VALUES[0] if ANALYSIS_STATE_VALUES else None),
        "daily_bias": analysis.get("daily_bias") or (DAILY_BIAS[0] if DAILY_BIAS else None),
        "fact_bias": analysis.get("fact_bias") or (DAILY_BIAS[0] if DAILY_BIAS else None),
        "day_result": analysis.get("day_result") or (DAY_RESULT_VALUES[0] if DAY_RESULT_VALUES else None),
    }


def _render_primary_fields(
    *,
    form_key: str,
    defaults: Dict[str, Any],
) -> Dict[str, Any]:
    date_value = st.date_input(
        "Date",
        value="today",
        format="DD.MM.YYYY",
        key=f"{form_key}_date",
    )
    asset_value = st.selectbox(
        "Asset",
        options=ASSETS,
        index=ASSETS.index(
            defaults["asset"]) if defaults["asset"] in ASSETS else 0,
        key=f"{form_key}_asset",
    )
    return {
        "date_local": date_value.isoformat(),
        "asset": asset_value,
    }


def render_analysis_creator(
    *,
    on_created: DialogCallback = None,
    on_cancel: Optional[Callable[[], None]] = None,
) -> None:
    """Диалог создания анализа."""

    @st.dialog("New analysis", width="small")
    def _dialog() -> None:
        defaults = _analysis_build_defaults()
        primary_payload = _render_primary_fields(
            form_key="analysis_create",
            defaults=defaults,
        )

        col1, col2 = st.columns(2)

        with col1:
            submitted = st.button(
                "Create",
                type="primary",
                width="stretch"
            )

        with col2:
            if not submitted:
                if st.button("Cancel", width="stretch"):
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

    defaults = _analysis_build_defaults(analysis)
    title = f"{defaults['asset']} · {defaults['date_local']}"

    @st.dialog(title, width="large")
    def _dialog() -> None:

        with st.container(border=True):
            def _submit_primary() -> None:
                st.session_state[f"analysis_submit_{analysis_id}"] = True

            def _cancel_primary() -> None:
                if on_close:
                    on_close()

            current_stage = defaults.get(
                "state") or ANALYSIS_STATE_VALUES[0]
            selected_stage = render_entity_header(
                status_label="Текущий этап",
                status_options=ANALYSIS_STATE_VALUES,
                current_status=current_stage,
                status_key=f"analysis_status_{analysis_id}",
                actions=[
                    {
                        "label": "Save changes",
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

        stage_map = _ensure_stage_records(analysis_id)
        visible_types = _visible_stage_types(selected_stage)

        for stage_type in ANALYSIS_STATE_VALUES:
            stage_data = stage_map.get(stage_type)
            render = stage_type in visible_types
            expanded = stage_type == selected_stage
            _render_stage_section(
                stage_type=stage_type,
                stage_data=stage_data,
                analysis=analysis,
                analysis_id=analysis_id,
                visible=render,
                expanded=expanded,
            )

        submitted_primary = st.session_state.pop(
            f"analysis_submit_{analysis_id}", False)
        if submitted_primary:
            try:
                update_analysis(
                    analysis_id,
                    {
                        "state": selected_stage,
                    },
                )
                st.success("Основные данные обновлены.")
                st.rerun()
            except Exception as exc:  # pragma: no cover
                st.error(f"Не удалось сохранить: {exc}")

        if st.button("Закрыть", use_container_width=True):
            if on_close:
                on_close()

    _dialog()


def _render_stage_section(
    *,
    stage_type: str,
    stage_data: Optional[Dict[str, Any]],
    analysis: Dict[str, Any],
    analysis_id: int,
    visible: bool,
    expanded: bool,
) -> None:
    if not visible or not stage_data:
        return
    stage_id = stage_data["id"]
    label = STAGE_TITLES.get(stage_type, stage_type.title())
    with st.expander(label, expanded=expanded):
        analysis_updates: Dict[str, Any] = {}
        if stage_type == "pre-market":
            analysis_updates["daily_bias"] = st.selectbox(
                "Daily bias",
                options=DAILY_BIAS,
                index=DAILY_BIAS.index(analysis.get("daily_bias")) if analysis.get(
                    "daily_bias") in DAILY_BIAS else 0,
                key=f"stage_daily_bias_{stage_id}",
            )
        if stage_type == "post-market":
            analysis_updates["fact_bias"] = st.selectbox(
                "Fact bias",
                options=DAILY_BIAS,
                index=DAILY_BIAS.index(analysis.get("fact_bias")) if analysis.get(
                    "fact_bias") in DAILY_BIAS else 0,
                key=f"stage_fact_bias_{stage_id}",
            )
            analysis_updates["day_result"] = st.selectbox(
                "Результат дня",
                options=DAY_RESULT_VALUES,
                index=DAY_RESULT_VALUES.index(analysis.get("day_result")) if analysis.get(
                    "day_result") in DAY_RESULT_VALUES else 0,
                key=f"stage_day_result_{stage_id}",
            )
        summary_value = st.text_area(
            "Описание",
            value=stage_data.get("summary") or "",
            height=220,
            key=f"stage_summary_{stage_id}",
        )

        st.markdown("#### Чарты")
        charts = list_analysis_stage_charts(stage_id)
        chart_rows_source = chart_table_rows(charts)
        chart_editor_value = render_chart_editor(
            key=f"chart_editor_stage_{stage_id}",
            base_rows=chart_rows_source,
            title="",
            caption=None,
        )

        st.markdown("#### Заметки")
        _render_stage_notes(stage_id=stage_id,
                            stage_key=f"notes_stage_{stage_id}")

        if st.button(
            "Сохранить этап",
            type="primary",
            use_container_width=True,
            key=f"save_stage_{stage_id}",
        ):
            stage_payload = {
                "analysis_id": analysis_id,
                "type": stage_type,
                "summary": summary_value.strip() or None,
                "time_local": datetime.now().strftime("%H:%M:%S"),
            }
            try:
                update_analysis_stage(stage_id, stage_payload)
                filtered_updates = {
                    key: value
                    for key, value in analysis_updates.items()
                    if value is not None
                }
                if filtered_updates:
                    update_analysis(analysis_id, filtered_updates)
                chart_state_payload = chart_editor_value if chart_editor_value is not None else chart_rows_source
                editor_rows = normalize_editor_rows(chart_state_payload)
                persist_chart_editor(
                    attached_charts=charts,
                    editor_rows=editor_rows,
                    attach_chart=lambda chart_id, s_id=stage_id: attach_chart_to_analysis_stage(
                        s_id, chart_id),
                )
                st.success("Этап обновлён.")
                st.rerun()
            except Exception as exc:  # pragma: no cover
                st.error(f"Не удалось сохранить этап: {exc}")


def _render_stage_notes(*, stage_id: int, stage_key: str) -> None:
    attached_notes = list_analysis_stage_notes(stage_id)
    all_notes = list_notes()
    note_ids = [note["id"] for note in all_notes]
    note_index = {note["id"]: note for note in all_notes}
    for note in attached_notes:
        if note["id"] not in note_index:
            note_index[note["id"]] = note
            note_ids.append(note["id"])

    selected_default = [note["id"] for note in attached_notes]
    selected_ids = st.multiselect(
        "Связанные заметки",
        options=note_ids,
        default=selected_default,
        key=f"notes_select_{stage_key}",
        format_func=lambda note_id: _note_label(note_index.get(note_id)),
    )
    _sync_stage_notes(
        stage_id=stage_id,
        current_ids=set(selected_default),
        selected_ids=set(selected_ids),
    )

    with st.popover("Создать заметку", use_container_width=True):
        new_note_title = st.text_input("Title", key=f"note_title_{stage_key}")
        new_note_body = st.text_area(
            "Body", key=f"note_body_{stage_key}", height=160)
        if st.button("Добавить", use_container_width=True, key=f"note_add_{stage_key}"):
            body_value = (new_note_body or "").strip()
            if not body_value:
                st.warning("Текст заметки не может быть пустым.")
            else:
                try:
                    note_id = add_note(new_note_title.strip()
                                       or None, body_value)
                    attach_note_to_analysis_stage(stage_id, note_id)
                    st.success("Заметка создана.")
                    st.rerun()
                except Exception as exc:  # pragma: no cover
                    st.error(f"Не удалось создать заметку: {exc}")


def _note_label(note: Optional[Dict[str, Any]]) -> str:
    if not note:
        return "Неизвестная заметка"
    title = (note.get("title") or "").strip()
    if title:
        return f"{title} (#{note['id']})"
    body = (note.get("body") or "").strip()
    if len(body) > 40:
        body = body[:37].rstrip() + "..."
    return f"{body or 'Untitled'} (#{note['id']})"


def _sync_stage_notes(
    *,
    stage_id: int,
    current_ids: Set[int],
    selected_ids: Set[int],
) -> None:
    to_attach = selected_ids - current_ids
    to_detach = current_ids - selected_ids
    if not to_attach and not to_detach:
        return
    try:
        for note_id in to_attach:
            attach_note_to_analysis_stage(stage_id, note_id)
        for note_id in to_detach:
            detach_note_from_analysis_stage(stage_id, note_id)
        st.success("Список заметок обновлён.")
        st.rerun()
    except Exception as exc:  # pragma: no cover
        st.error(f"Не удалось обновить заметки: {exc}")


def _visible_stage_types(current_stage: str) -> List[str]:
    if current_stage not in ANALYSIS_STATE_VALUES:
        return [ANALYSIS_STATE_VALUES[0]]
    idx = ANALYSIS_STATE_VALUES.index(current_stage)
    return ANALYSIS_STATE_VALUES[: idx + 1]


def _ensure_stage_records(analysis_id: int) -> Dict[str, Dict[str, Any]]:
    stage_map: Dict[str, Dict[str, Any]] = {}
    for stage in list_analysis_stages({"analysis_id": analysis_id}):
        stage_map[stage["type"]] = stage
    for stage_type in ANALYSIS_STATE_VALUES:
        if stage_type in stage_map:
            continue
        new_id = add_analysis_stage({
            "analysis_id": analysis_id,
            "type": stage_type,
            "time_local": datetime.now().strftime("%H:%M:%S"),
            "summary": None,
        })
        new_stage = get_analysis_stage(new_id)
        if new_stage:
            stage_map[stage_type] = new_stage
        else:  # fallback
            stage_map[stage_type] = {
                "id": new_id,
                "analysis_id": analysis_id,
                "type": stage_type,
                "time_local": datetime.now().strftime("%H:%M:%S"),
                "summary": None,
            }
    return stage_map


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
