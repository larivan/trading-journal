"""Переиспользуемые UI-хелперы для работы с изображениями и их привязками."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import streamlit as st

from db import add_image, delete_image, update_image

_DIR = Path(__file__).parent
_COMPONENT_HTML = (_DIR / "template.html").read_text(encoding="utf-8")
_COMPONENT_CSS = (_DIR / "styles.css").read_text(encoding="utf-8")
_COMPONENT_JS = (_DIR / "script.js").read_text(encoding="utf-8")

ImageRow = Dict[str, Any]


def image_editor_value_state_key(widget_key: str) -> str:
    """Возвращает ключ session_state для хранения данных редактора."""
    return f"{widget_key}__value"


def _layout_from_columns(columns: int) -> str:
    if columns >= 3:
        return "grid3"
    if columns == 2:
        return "grid2"
    return "column"


def _sanitize_image_rows(
    rows: Sequence[ImageRow],
    *,
    keep_empty: bool = False,
) -> List[ImageRow]:
    sanitized: List[ImageRow] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        image_url = str(row.get("image_url") or "").strip()
        cleaned = {
            "id": row.get("id"),
            "image_url": image_url,
            "caption": (row.get("caption") or "").strip(),
        }
        if image_url or keep_empty:
            sanitized.append(cleaned)
    return sanitized


_image_editor_component = st.components.v2.component(
    "image_editor",
    html=_COMPONENT_HTML,
    css=_COMPONENT_CSS,
    js=_COMPONENT_JS,
)


def render_image_editor(
    *,
    key: str,
    base_rows: Sequence[ImageRow],
    layout_columns: int = 1,
) -> List[ImageRow]:
    """Отрисовывает универсальный редактор изображений и возвращает его значение."""
    sanitized_rows = _sanitize_image_rows(base_rows)
    layout_mode = _layout_from_columns(layout_columns)
    value_state_key = image_editor_value_state_key(key)

    callbacks = {
        "on_charts_change": lambda: None,
    }

    result = _image_editor_component(
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
        sanitized_value = _sanitize_image_rows(charts_value, keep_empty=True)
        st.session_state[value_state_key] = sanitized_value
        return sanitized_value

    cached_value = st.session_state.get(value_state_key)
    if isinstance(cached_value, list):
        sanitized_cached = _sanitize_image_rows(cached_value, keep_empty=True)
        st.session_state[value_state_key] = sanitized_cached
        return sanitized_cached

    st.session_state[value_state_key] = sanitized_rows
    return sanitized_rows


def image_table_rows(images: List[ImageRow]) -> List[ImageRow]:
    """Готовит строки изображения для редактора."""
    return [
        {
            "id": image.get("id"),
            "image_url": image.get("image_url") or "",
            "caption": image.get("caption") or "",
        }
        for image in images
    ]


def normalize_editor_rows(editor_value: Any) -> List[ImageRow]:
    """Приводит ответ data_editor к списку словарей."""
    if isinstance(editor_value, list):
        raw_rows = editor_value
    elif hasattr(editor_value, "to_dict"):
        raw_rows = editor_value.to_dict("records")  # type: ignore[call-arg]
    else:
        raw_rows = []

    normalized: List[ImageRow] = []
    for row in raw_rows:
        image_url = (row.get("image_url") or "").strip()
        normalized.append({
            "id": row.get("id"),
            "image_url": image_url,
            "caption": row.get("caption") or "",
        })
    return normalized


def persist_image_editor(
    *,
    attached_images: List[ImageRow],
    editor_rows: List[ImageRow],
    attach_image: Callable[[int], None],
    conn: Optional[Any] = None,
) -> None:
    """Синхронизирует таблицу изображений с данными из редактора."""
    desired_rows: List[ImageRow] = []
    for row in editor_rows:
        image_url = (row.get("image_url") or "").strip()
        if not image_url:
            continue
        desired_rows.append({
            "id": _clean_image_id(row.get("id")),
            "image_url": image_url,
            "caption": (row.get("caption") or "").strip() or None,
        })

    current_by_id = {image["id"]: image for image in attached_images}
    desired_ids = {row["id"] for row in desired_rows if row["id"] is not None}

    for image_id in set(current_by_id.keys()) - desired_ids:
        if image_id is not None:
            try:
                delete_image(image_id, conn=conn)
            except ValueError:
                pass  # already deleted — desired state achieved

    for row in desired_rows:
        image_id = row.get("id")
        if image_id is None or image_id not in current_by_id:
            continue
        existing = current_by_id[image_id]
        existing_url = (existing.get("image_url") or "").strip()
        existing_caption = (existing.get("caption") or None)
        if row["image_url"] != existing_url or row["caption"] != existing_caption:
            update_image(image_id, row["image_url"], row["caption"], conn=conn)

    for row in desired_rows:
        if row.get("id") is not None:
            continue
        image_id = add_image(row["image_url"], row["caption"], conn=conn)
        # Внешняя функция решает, к какой сущности привязать изображение.
        attach_image(image_id)


def _clean_image_id(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
