"""Секция управления списком планов внутри этапа plan."""

from __future__ import annotations
from typing import Any, Dict, List, Tuple
from uuid import uuid4
import streamlit as st
from components.vertical_tabs import render_vertical_tabs
from components.chart_editor import (
    chart_editor_value_state_key,
    chart_table_rows,
    render_chart_editor,
)


PlanEntry = Dict[str, Any]


def render_plan_section(
    *,
    plan_entries: List[PlanEntry],
    visible: bool,
    expanded: bool,
    state_key: str,
) -> Tuple[List[Dict[str, Any]], List[int]]:
    """Отрисовывает планы и возвращает формы + список удаленных stage_id."""

    if not visible:
        return [], []

    entries_key = f"{state_key}_plans"
    removed_key = f"{state_key}_plans_removed"
    if entries_key not in st.session_state:
        st.session_state[entries_key] = [
            {
                "key": entry.get("key") or str(entry.get("stage_id") or uuid4().hex),
                "stage_id": entry.get("stage_id"),
                "summary": entry.get("summary") or "",
                "charts": entry.get("charts") or [],
                "time_local": entry.get("time_local"),
            }
            for entry in (plan_entries or [])
        ] or [_empty_entry()]
    st.session_state.setdefault(removed_key, [])

    entries: List[PlanEntry] = st.session_state[entries_key]
    removed_ids: List[int] = st.session_state[removed_key]

    with st.expander("Plan", expanded=expanded):
        tabs = [
            {"id": entry["key"], "label": _tab_label(idx, entry)}
            for idx, entry in enumerate(entries, start=1)
        ]
        selected_tab, content_col = render_vertical_tabs(
            key=f"{state_key}_tabs",
            tabs=tabs,
            label="Plans",
            add_label="Add plan",
            remove_label="×",
            min_tabs=1,
            on_add=lambda: st.session_state.setdefault(
                entries_key, []).append(_empty_entry()),
            on_remove=lambda tab: _remove_entry(
                entries_key, removed_key, state_key, tab),
        )

        if selected_tab:
            active = next(
                (item for item in entries if item["key"]
                 == selected_tab["id"]), None
            )
            if active:
                _render_entry(active, content_col, state_key)

    forms: List[Dict[str, Any]] = []
    for entry in entries:
        chart_rows = chart_table_rows(entry.get("charts") or [])
        chart_key = _chart_editor_key(state_key, entry["key"])
        summary_key = _summary_key(state_key, entry["key"])
        forms.append(
            {
                "stage_id": entry.get("stage_id"),
                "stage_type": "plan",
                "summary": st.session_state.get(summary_key, entry.get("summary") or ""),
                "charts": {
                    "rows_source": chart_rows,
                    "editor_value": st.session_state.get(
                        chart_editor_value_state_key(chart_key), chart_rows
                    ),
                },
                "entry_key": entry["key"],
                "time_local": entry.get("time_local"),
            }
        )

    return forms, removed_ids


def _render_entry(entry: PlanEntry, container: Any, state_key: str) -> None:
    chart_rows = chart_table_rows(entry.get("charts") or [])
    with container:
        st.markdown("#### Charts")
        render_chart_editor(
            key=_chart_editor_key(state_key, entry["key"]),
            base_rows=chart_rows,
            layout_columns=2,
        )
        st.divider()
        st.text_area(
            "Plan notes",
            value=entry.get("summary") or "",
            key=_summary_key(state_key, entry["key"]),
            height=160,
        )


def _remove_entry(
    entries_key: str,
    removed_key: str,
    state_key: str,
    tab: Any,
) -> None:
    entry_id = tab.get("id") if isinstance(tab, dict) else None
    if entry_id is None:
        return

    entries = st.session_state.get(entries_key, [])
    remaining: List[PlanEntry] = []
    for item in entries:
        if item.get("key") != entry_id:
            remaining.append(item)
            continue
        stage_id = item.get("stage_id")
        if stage_id:
            removed = st.session_state.setdefault(removed_key, [])
            if stage_id not in removed:
                removed.append(stage_id)
        st.session_state.pop(_summary_key(state_key, entry_id), None)
        st.session_state.pop(
            chart_editor_value_state_key(
                _chart_editor_key(state_key, entry_id)), None
        )

    st.session_state[entries_key] = remaining or [_empty_entry()]


def _empty_entry() -> PlanEntry:
    return {
        "key": uuid4().hex,
        "stage_id": None,
        "summary": "",
        "charts": [],
        "time_local": None,
    }


def _tab_label(idx: int, entry: PlanEntry) -> str:
    base = f"Plan №{idx}"
    stage_time = (entry.get("time_local") or "").strip()
    return f"{base} · {stage_time}" if stage_time else base


def _chart_editor_key(state_key: str, entry_key: str) -> str:
    return f"{state_key}_chart_{entry_key}"


def _summary_key(state_key: str, entry_key: str) -> str:
    return f"{state_key}_summary_{entry_key}"


__all__ = ["render_plan_section"]
