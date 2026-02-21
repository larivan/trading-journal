"""Переиспользуемые UI-хелперы для работы с чартами и их привязками."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import streamlit as st

from db import add_chart, delete_chart, update_chart

_DIR = Path(__file__).parent
_COMPONENT_HTML = (_DIR / "template.html").read_text(encoding="utf-8")
_COMPONENT_CSS = (_DIR / "styles.css").read_text(encoding="utf-8")
_COMPONENT_JS = (_DIR / "script.js").read_text(encoding="utf-8")

ChartRow = Dict[str, Any]


def chart_editor_value_state_key(widget_key: str) -> str:
    """Возвращает ключ session_state для хранения данных редактора."""
    return f"{widget_key}__value"


def _layout_from_columns(columns: int) -> str:
    if columns >= 3:
        return "grid3"
    if columns == 2:
        return "grid2"
    return "column"


def _sanitize_chart_rows(
    rows: Sequence[ChartRow],
    *,
    keep_empty: bool = False,
) -> List[ChartRow]:
    sanitized: List[ChartRow] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        chart_url = str(row.get("chart_url") or "").strip()
        cleaned = {
            "id": row.get("id"),
            "chart_url": chart_url,
            "caption": (row.get("caption") or "").strip(),
        }
        if chart_url or keep_empty:
            sanitized.append(cleaned)
    return sanitized


_chart_editor_component = st.components.v2.component(
    "chart_editor",
    html=_COMPONENT_HTML,
    css=_COMPONENT_CSS,
    js=_COMPONENT_JS,
)


def render_chart_editor(
    *,
    key: str,
    base_rows: Sequence[ChartRow],
    layout_columns: int = 1,
) -> List[ChartRow]:
    """Отрисовывает универсальный редактор чартов и возвращает его значение."""
    sanitized_rows = _sanitize_chart_rows(base_rows)
    layout_mode = _layout_from_columns(layout_columns)
    value_state_key = chart_editor_value_state_key(key)

    callbacks = {
        "on_charts_change": lambda: None,
    }

    result = _chart_editor_component(
        key=key,
        data={
            "charts": sanitized_rows,
            "layout": layout_mode,
        },
        default={"charts": sanitized_rows},
        **callbacks,
    )

    charts_value = result.get("charts") if isinstance(result, dict) else None
    if isinstance(charts_value, list):
        sanitized_value = _sanitize_chart_rows(charts_value, keep_empty=True)
        st.session_state[value_state_key] = sanitized_value
        return sanitized_value

    cached_value = st.session_state.get(value_state_key)
    if isinstance(cached_value, list):
        sanitized_cached = _sanitize_chart_rows(cached_value, keep_empty=True)
        st.session_state[value_state_key] = sanitized_cached
        return sanitized_cached

    st.session_state[value_state_key] = sanitized_rows
    return sanitized_rows


def chart_table_rows(charts: List[ChartRow]) -> List[ChartRow]:
    """Готовит строки чарта для редактора."""
    return [
        {
            "id": chart.get("id"),
            "chart_url": chart.get("chart_url") or "",
            "caption": chart.get("caption") or "",
        }
        for chart in charts
    ]


def normalize_editor_rows(editor_value: Any) -> List[ChartRow]:
    """Приводит ответ data_editor к списку словарей."""
    if isinstance(editor_value, list):
        raw_rows = editor_value
    elif hasattr(editor_value, "to_dict"):
        raw_rows = editor_value.to_dict("records")  # type: ignore[call-arg]
    else:
        raw_rows = []

    normalized: List[ChartRow] = []
    for row in raw_rows:
        chart_url = (row.get("chart_url") or "").strip()
        normalized.append({
            "id": row.get("id"),
            "chart_url": chart_url,
            "caption": row.get("caption") or "",
        })
    return normalized


def persist_chart_editor(
    *,
    attached_charts: List[ChartRow],
    editor_rows: List[ChartRow],
    attach_chart: Callable[[int], None],
    conn: Optional[Any] = None,
) -> None:
    """Синхронизирует таблицу чартов с данными из редактора."""
    desired_rows: List[ChartRow] = []
    for row in editor_rows:
        chart_url = (row.get("chart_url") or "").strip()
        if not chart_url:
            continue
        desired_rows.append({
            "id": _clean_chart_id(row.get("id")),
            "chart_url": chart_url,
            "caption": (row.get("caption") or "").strip() or None,
        })

    current_by_id = {chart["id"]: chart for chart in attached_charts}
    desired_ids = {row["id"] for row in desired_rows if row["id"] is not None}

    for chart_id in set(current_by_id.keys()) - desired_ids:
        if chart_id is not None:
            delete_chart(chart_id, conn=conn)

    for row in desired_rows:
        chart_id = row.get("id")
        if chart_id is None or chart_id not in current_by_id:
            continue
        existing = current_by_id[chart_id]
        existing_url = (existing.get("chart_url") or "").strip()
        existing_caption = (existing.get("caption") or None)
        if row["chart_url"] != existing_url or row["caption"] != existing_caption:
            update_chart(chart_id, row["chart_url"], row["caption"], conn=conn)

    for row in desired_rows:
        if row.get("id") is not None:
            continue
        chart_id = add_chart(row["chart_url"], row["caption"], conn=conn)
        # Внешняя функция решает, к какой сущности привязать чарт.
        attach_chart(chart_id)


def _clean_chart_id(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
