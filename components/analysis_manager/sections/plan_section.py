"""Секция управления списком планов внутри этапа plan."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import streamlit as st

from components.chart_editor import (
    chart_editor_value_state_key,
    chart_table_rows,
    render_chart_editor,
)
from components.vertical_tabs import render_vertical_tabs


PlanEntry = Dict[str, Any]


def render_plan_section(
    *,
    plan_entries: List[PlanEntry],
    key_prefix: str,
    visible: bool,
    expanded: bool,
    on_add: Callable[[], None],
    on_remove: Callable[[PlanEntry], None],
) -> List[Dict[str, Any]]:
    """Отображает список планов и возвращает их формы."""

    if not visible:
        return []

    if not plan_entries:
        on_add()
        return []

    forms: List[Dict[str, Any]] = []

    with st.expander("Plan", expanded=expanded):
        tabs = [
            {
                "id": entry["key"],
                "label": _format_tab_label(idx, entry),
            }
            for idx, entry in enumerate(plan_entries, start=1)
        ]

        tab_lookup = {entry["key"]: entry for entry in plan_entries}

        def _handle_remove(tab: Optional[Dict[str, Any]]) -> None:
            if not tab:
                return
            entry = tab_lookup.get(tab["id"])
            if entry:
                on_remove(entry)

        selected_tab, content_col = render_vertical_tabs(
            key=f"plan_tabs_{key_prefix}",
            tabs=tabs,
            label="Plans",
            add_label="Add new",
            remove_label="×",
            min_tabs=1,
            on_add=on_add,
            on_remove=_handle_remove,
        )

        if selected_tab:
            entry = tab_lookup.get(selected_tab["id"])
            if entry:
                _render_plan_entry(entry, content_col, key_prefix)

        for entry in plan_entries:
            rows_source = entry.get("rows_source")
            if rows_source is None:
                rows_source = chart_table_rows(entry.get("charts") or [])
                entry["rows_source"] = rows_source
            chart_editor_key = _chart_editor_key(key_prefix, entry["key"])
            editor_value = entry.get("chart_editor_value")
            if editor_value is None:
                editor_value = st.session_state.get(
                    chart_editor_value_state_key(chart_editor_key)
                )
            forms.append(
                {
                    "stage_id": entry.get("stage_id"),
                    "stage_type": "plan",
                    "summary": entry.get("summary") or "",
                    "charts": {
                        "attached": entry.get("charts") or [],
                        "rows_source": rows_source,
                        "editor_value": editor_value,
                    },
                    "entry_key": entry["key"],
                }
            )

    return forms


def _render_plan_entry(entry: PlanEntry, container: Any, key_prefix: str) -> None:
    rows_source = entry.get("rows_source")
    if rows_source is None:
        rows_source = chart_table_rows(entry.get("charts") or [])
        entry["rows_source"] = rows_source

    with container:
        chart_editor_value = render_chart_editor(
            key=_chart_editor_key(key_prefix, entry["key"]),
            base_rows=rows_source,
            layout_columns=2
        )
        entry["chart_editor_value"] = chart_editor_value

        summary_value = st.text_area(
            "Plan Notes",
            value=entry.get("summary") or "",
            height=160,
            key=_summary_key(key_prefix, entry["key"]),
        )
        entry["summary"] = summary_value


def _format_tab_label(idx: int, entry: PlanEntry) -> str:
    label = f"Plan №{idx}"
    stage_time = (entry.get("time_local") or "").strip()
    if stage_time:
        label = f"{label} · {stage_time}"
    return label


def _summary_key(prefix: str, entry_key: str) -> str:
    return f"{prefix}_plan_summary_{entry_key}"


def _chart_editor_key(prefix: str, entry_key: str) -> str:
    return f"plan_chart_editor_{prefix}_{entry_key}"


__all__ = ["render_plan_section"]
