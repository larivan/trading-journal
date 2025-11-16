"""Секция управления списком планов внутри этапа plan."""

from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st

from components.chart_editor import (
    chart_editor_value_state_key,
    chart_table_rows,
    render_chart_editor,
)
from components.vertical_tabs import render_vertical_tabs
from db import (
    add_analysis_stage,
    delete_analysis_stage,
    list_analysis_stage_charts,
)

from ..constants import STAGE_TITLES


def render_plan_section(
    *,
    plan_stages: List[Dict[str, Any]],
    analysis_id: int,
    visible: bool,
    expanded: bool,
) -> List[Dict[str, Any]]:
    """Отображает список планов и возвращает их формы."""

    if not visible:
        return []

    stage_label = STAGE_TITLES.get("plan", "Plan")
    forms: List[Dict[str, Any]] = []

    with st.expander(stage_label, expanded=expanded):
        sorted_stages = sorted(plan_stages, key=lambda s: s.get("id") or 0)

        if not sorted_stages:
            _create_plan_stage(analysis_id)
            st.rerun()
            return []

        charts_cache: Dict[int, List[Dict[str, Any]]] = {}
        rows_cache: Dict[int, List[Dict[str, Any]]] = {}
        for stage in sorted_stages:
            stage_id = stage["id"]
            charts = list_analysis_stage_charts(stage_id)
            chart_rows_source = chart_table_rows(charts)
            charts_cache[stage_id] = charts
            rows_cache[stage_id] = chart_rows_source

        tabs = [
            {
                "id": stage["id"],
                "label": _format_tab_label(idx, stage),
            }
            for idx, stage in enumerate(sorted_stages, start=1)
        ]

        def _add_plan() -> None:
            _create_plan_stage(analysis_id)
            st.success("План создан.")
            st.rerun()

        def _remove_plan(tab: Dict[str, Any]) -> None:
            stage_id = tab.get("id")
            if stage_id is None:
                return
            try:
                delete_analysis_stage(stage_id)
                st.success("План удалён.")
                st.rerun()
            except Exception as exc:  # pragma: no cover
                st.error(f"Не удалось удалить план: {exc}")

        selected_tab, content_col = render_vertical_tabs(
            key=f"plan_tabs_{analysis_id}",
            tabs=tabs,
            label="Plans",
            add_label="Add new",
            remove_label="×",
            min_tabs=1,
            on_add=_add_plan,
            on_remove=_remove_plan,
        )

        if not selected_tab:
            return []

        stage_map = {stage["id"]: stage for stage in sorted_stages}
        selected_stage = stage_map.get(selected_tab["id"])
        if not selected_stage:
            return []

        summary_key = _summary_key(selected_stage["id"])
        chart_key = _chart_editor_key(selected_stage["id"])

        summary_values: Dict[int, str] = {}
        editor_values: Dict[int, Any] = {}

        with content_col:
            editor_values[selected_stage["id"]] = render_chart_editor(
                key=chart_key,
                base_rows=rows_cache[selected_stage["id"]],
                title="Charts",
                caption=None,
            )
            summary_values[selected_stage["id"]] = st.text_area(
                "Note",
                value=selected_stage.get("summary") or "",
                height=200,
                key=summary_key,
            )

        for stage in sorted_stages:
            stage_id = stage["id"]
            forms.append(
                {
                    "stage_id": stage_id,
                    "stage_type": "plan",
                    "summary": summary_values.get(
                        stage_id,
                        st.session_state.get(
                            _summary_key(stage_id),
                            stage.get("summary") or "",
                        ),
                    ),
                    "charts": {
                        "attached": charts_cache.get(stage_id) or [],
                        "rows_source": rows_cache.get(stage_id) or [],
                        "editor_value": editor_values.get(
                            stage_id,
                            st.session_state.get(
                                chart_editor_value_state_key(_chart_editor_key(stage_id))
                            ),
                        ),
                    },
                }
            )

    return forms


def _format_tab_label(idx: int, stage: Dict[str, Any]) -> str:
    label = f"Plan №{idx}"
    stage_time = (stage.get("time_local") or "").strip()
    if stage_time:
        label = f"{label} · {stage_time}"
    return label


def _summary_key(stage_id: int) -> str:
    return f"plan_summary_{stage_id}"


def _chart_editor_key(stage_id: int) -> str:
    return f"plan_chart_editor_{stage_id}"


def _create_plan_stage(analysis_id: int) -> None:
    add_analysis_stage(
        {
            "analysis_id": analysis_id,
            "type": "plan",
            "time_local": None,
            "summary": None,
        }
    )


__all__ = ["render_plan_section"]
