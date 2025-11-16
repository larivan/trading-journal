"""Dialogs and helpers for managing daily analyses and their stages."""

from __future__ import annotations

from typing import Callable, Optional

import streamlit as st

from components.state_header import render_entity_header
from config import ANALYSIS_STATE_VALUES
from db import add_analysis, delete_analysis, get_analysis, update_analysis

from .defaults import build_analysis_defaults
from .sections import render_primary_fields, render_stage_section
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

    defaults = build_analysis_defaults(analysis)
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

        stage_map = ensure_stage_records(analysis_id)
        visible_types = visible_stage_types(selected_stage)

        for stage_type in ANALYSIS_STATE_VALUES:
            stage_data = stage_map.get(stage_type)
            render = stage_type in visible_types
            expanded = stage_type == selected_stage
            render_stage_section(
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
