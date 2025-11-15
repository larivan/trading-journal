"""Переиспользуемые UI-хелперы для работы с чартами и их привязками."""

from typing import Any, Callable, Dict, List, Optional

import streamlit as st

from db import add_chart, delete_chart, update_chart

ChartRow = Dict[str, Any]


def render_chart_editor(
    *,
    key: str,
    base_rows: List[ChartRow],
    title: str = "Charts",
    caption: Optional[str] = "Paste links to your TradingView snapshots so they stay linked to this record.",
) -> Any:
    """Отрисовывает универсальный редактор чартов и возвращает его значение."""
    if title:
        st.subheader(title)
    if caption:
        st.caption(caption)
    return st.data_editor(
        base_rows,
        key=key,
        num_rows="dynamic",
        hide_index=True,
        column_order=["chart_url", "caption"],
        column_config={
            "chart_url": st.column_config.LinkColumn(
                "Chart URL",
                required=True,
                help="Paste a direct image link.",
                validate=r"^https?:\/\/(?:www\.)?tradingview\.com\/.+\/?$",
            ),
            "caption": st.column_config.TextColumn(
                "Caption",
                required=False,
            ),
            "id": st.column_config.Column(
                "ID",
                disabled=True,
                required=False,
                width="small",
            ),
        },
    )


def chart_table_rows(charts: List[ChartRow]) -> List[ChartRow]:
    """Готовит строки чарта для data_editor, даже если данных нет."""
    rows = [
        {
            "id": chart.get("id"),
            "chart_url": chart.get("chart_url") or "",
            "caption": chart.get("caption") or "",
        }
        for chart in charts
    ]
    if rows:
        return rows
    return [{
        "id": None,
        "chart_url": "",
        "caption": "",
    }]


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
            delete_chart(chart_id)

    for row in desired_rows:
        chart_id = row.get("id")
        if chart_id is None or chart_id not in current_by_id:
            continue
        existing = current_by_id[chart_id]
        existing_url = (existing.get("chart_url") or "").strip()
        existing_caption = (existing.get("caption") or None)
        if row["chart_url"] != existing_url or row["caption"] != existing_caption:
            update_chart(chart_id, row["chart_url"], row["caption"])

    for row in desired_rows:
        if row.get("id") is not None:
            continue
        chart_id = add_chart(row["chart_url"], row["caption"])
        attach_chart(chart_id)  # Внешняя функция решает, к какой сущности привязать чарт.


def _clean_chart_id(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
