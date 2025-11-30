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
    expanded: bool
) -> List[Dict[str, Any]]:
    """Отображает список планов и возвращает их формы."""

    if not visible:
        return []

    if not plan_entries:
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
                _remove_plan_entry(entry)

        selected_tab, content_col = render_vertical_tabs(
            key=f"plan_tabs_new",
            tabs=tabs,
            label="Plans",
            add_label="Add new",
            remove_label="×",
            min_tabs=1,
            on_add=_add_plan_entry,
            on_remove=_handle_remove,
        )

        if selected_tab:
            active_entry = tab_lookup.get(selected_tab["id"])
            if active_entry:
                _render_plan_entry(active_entry, content_col)

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


def _render_plan_entry(entry: PlanEntry, container: Any) -> None:
    rows_source = entry.get("rows_source")
    if rows_source is None:
        rows_source = chart_table_rows(entry.get("charts") or [])
        entry["rows_source"] = rows_source

    with container:
        entry["chart_editor_value"] = render_chart_editor(
            key="sdfsdfsdfskjhgfks",
            base_rows=rows_source,
            layout_columns=2
        )

        entry["summary"] = st.text_area(
            "Plan Notes",
            value=entry.get("summary") or "",
            height=160,
        )


def _format_tab_label(idx: int, entry: PlanEntry) -> str:
    label = f"Plan №{idx}"
    stage_time = (entry.get("time_local") or "").strip()
    if stage_time:
        label = f"{label} · {stage_time}"
    return label


def _empty_plan_entry(context_key: str) -> Dict[str, Any]:
    return {
        "key": uuid4().hex,
        "stage_id": None,
        "summary": "",
        "charts": [],
        "rows_source": None,
        "time_local": None,
    }


def _add_plan_entry(context_key: str) -> None:
    entries = st.session_state.setdefault(_plan_entries_key(context_key), [])
    entries.append(_empty_plan_entry(context_key))
    st.session_state[_plan_entries_key(context_key)] = entries


def _remove_plan_entry(context_key: str, entry: Optional[Dict[str, Any]]) -> None:
    if not entry:
        return
    entries = st.session_state.get(_plan_entries_key(context_key), [])
    stage_id = entry.get("stage_id")
    if stage_id:
        removed_ids = st.session_state.setdefault(
            _removed_plan_ids_key(context_key), []
        )
        if stage_id not in removed_ids:
            removed_ids.append(stage_id)
    entries = [item for item in entries if item["key"] != entry["key"]]
    if not entries:
        entries.append(_empty_plan_entry(context_key))
    st.session_state[_plan_entries_key(context_key)] = entries
    _cleanup_plan_entry_state(context_key, entry["key"])


def _cleanup_plan_entry_state(context_key: str, entry_key: str) -> None:
    summary_key = f"{context_key}_plan_summary_{entry_key}"
    st.session_state.pop(summary_key, None)
    chart_key = f"plan_chart_editor_{context_key}_{entry_key}"
    st.session_state.pop(chart_editor_value_state_key(chart_key), None)


__all__ = ["render_plan_section"]
