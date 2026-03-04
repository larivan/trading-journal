"""Блок Review."""

from typing import Any, Dict, List, Optional
import streamlit as st


def render_review_stage(
    *,
    defaults: Dict[str, Any],
    state_key: str,
    mistake_type_options: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Показывает блок Review."""
    data = defaults.copy()
    if mistake_type_options is None:
        mistake_type_options = []

    selected_mistakes = st.multiselect(
        "Mistake types",
        options=mistake_type_options,
        default=data.get("mistake_types") or [],
        placeholder="No mistakes",
        key=f"{state_key}_mistake_types",
    )
    data["mistake_types"] = selected_mistakes

    is_reviewed = st.checkbox(
        "Mark as reviewed",
        value=data.get("is_correct") is not None,
        key=f"{state_key}_is_reviewed",
    )

    if is_reviewed:
        data["is_correct"] = 0 if selected_mistakes else 1
    else:
        data["is_correct"] = None
        data["mistake_types"] = []

    return data
