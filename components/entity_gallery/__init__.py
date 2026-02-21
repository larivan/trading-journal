"""Custom component that renders entity data as a card gallery."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import streamlit as st

from utils.session_state import EntityName, handle_selection_change

_DIR = Path(__file__).parent
_COMPONENT_HTML = (_DIR / "template.html").read_text(encoding="utf-8")
_COMPONENT_CSS = (_DIR / "styles.css").read_text(encoding="utf-8")
_COMPONENT_JS = (_DIR / "script.js").read_text(encoding="utf-8")

ColumnDefinition = Dict[str, Any]

_entity_gallery_component = st.components.v2.component(
    "entity_gallery",
    html=_COMPONENT_HTML,
    css=_COMPONENT_CSS,
    js=_COMPONENT_JS,
)


def _format_cell_value(value: Any, column: ColumnDefinition) -> str:
    """Format a column value as text for display."""
    if value is None:
        return ""
    formatter = column.get("format")
    if callable(formatter):
        try:
            return str(formatter(value))
        except Exception:  # noqa: BLE001 — caller-supplied formatter may raise anything
            return str(value)
    return str(value)


def _normalize_columns(
    columns: Sequence[ColumnDefinition],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    normalized: List[Dict[str, Any]] = []
    order: List[str] = []
    for index, column in enumerate(columns):
        field = column.get("field")
        col_key = column.get("id") or column.get(
            "key") or field or f"col_{index}"
        label = column.get("label") or field or col_key
        role = column.get("role")
        normalized.append(
            {
                "key": str(col_key),
                "label": str(label),
                "field": field,
                "role": str(role) if role else None,
                "hidden": bool(column.get("hidden")),
                "compute": column.get("compute"),
                "format": column.get("format"),
            }
        )
        order.append(str(col_key))
    return normalized, order


def _build_rows_payload(
    *,
    rows: Sequence[Dict[str, Any]],
    id_field: str,
    columns: Sequence[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[Any, Dict[str, Any]]]:
    processed_rows: List[Dict[str, Any]] = []
    id_to_row: Dict[Any, Dict[str, Any]] = {}
    for row in rows:
        row_id = row.get(id_field)
        if row_id is None:
            continue
        id_to_row[row_id] = row
        cells: Dict[str, Any] = {}
        for col in columns:
            col_key = col["key"]
            field = col.get("field")
            value: Any
            compute = col.get("compute")
            if callable(compute):
                try:
                    value = compute(row)
                except Exception:  # noqa: BLE001 — caller-supplied compute may raise anything
                    value = None
            elif field:
                value = row.get(field)
            else:
                value = None
            cells[col_key] = _format_cell_value(value, col)
        processed_rows.append({"id": row_id, "cells": cells})
    return processed_rows, id_to_row


def render_entity_gallery(
    *,
    entity_name: EntityName,
    key: str,
    rows: Sequence[Dict[str, Any]],
    columns: Sequence[ColumnDefinition],
    id_field: str = "id",
    empty_message: str = "No data to display.",
    page_size: int = 12,
    on_open: Optional[Callable[[Dict[str, Any]], None]] = None,
    on_delete: Optional[Callable[[List[Any]], None]] = None,
    enable_selection: Optional[bool] = None,
) -> None:
    """Render a gallery of cards for arbitrary entities.

    Columns may specify role: title, subtitle, text, detail, hidden.
    """
    if not rows:
        st.info(empty_message)
        handle_selection_change(entity_name, [])
        return

    component_state = st.session_state.get(key, {})
    initial_selected = (
        list(component_state.get("selected_ids") or [])
        if isinstance(component_state, dict)
        else []
    )
    raw_page = component_state.get("page") if isinstance(
        component_state, dict) else 0
    initial_page = int(raw_page) if isinstance(
        raw_page, int) and raw_page >= 0 else 0

    normalized_columns, _ = _normalize_columns(columns)
    rows_payload, id_to_row = _build_rows_payload(
        rows=rows,
        id_field=id_field,
        columns=normalized_columns,
    )

    selection_enabled = True if enable_selection is None else bool(
        enable_selection)

    callbacks: Dict[str, Callable[[], None]] = {
        "on_selected_ids_change": lambda: None,
        "on_open_change": lambda: None,
        "on_delete_change": lambda: None,
        "on_page_change": lambda: None,
    }

    result = _entity_gallery_component(
        key=key,
        data={
            "rows": rows_payload,
            "columns": [
                {
                    "key": col["key"],
                    "label": col["label"],
                    "role": col.get("role"),
                    "hidden": col.get("hidden", False),
                }
                for col in normalized_columns
            ],
            "pageSize": max(1, int(page_size)),
            "page": initial_page,
            "selectedIds": initial_selected if selection_enabled else [],
            "allowSelection": selection_enabled,
            "allowOpen": bool(on_open),
        },
        default={
            "selected_ids": initial_selected if selection_enabled else [],
            "page": initial_page,
        },
        **callbacks,
    )

    if not isinstance(result, dict):
        handle_selection_change(entity_name, initial_selected)
        return

    selected_ids = result.get("selected_ids") or initial_selected
    if not isinstance(selected_ids, list):
        selected_ids = initial_selected

    open_id = result.get("open")
    delete_ids = result.get("delete")

    if on_open is not None and open_id is not None:
        row = id_to_row.get(open_id)
        if row is not None:
            on_open(row)
            st.rerun()

    if on_delete is not None and isinstance(delete_ids, list) and delete_ids:
        on_delete(delete_ids)

    if selection_enabled:
        handle_selection_change(entity_name, selected_ids)
    else:
        handle_selection_change(entity_name, [])


__all__ = ["render_entity_gallery", "ColumnDefinition"]
