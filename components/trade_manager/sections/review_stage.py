"""Блок Review."""

from typing import Any, Dict, Optional
import streamlit as st


def render_review_stage(
    *,
    visible: bool,
    expanded: bool,
    defaults: Dict[str, Any],
    state_key: str
) -> Optional[Dict[str, Any]]:
    """Показывает блок Review, если он нужен для текущего статуса."""
    data = defaults.copy()
    if not visible:
        return None

    with st.expander("Reviewed", expanded=expanded):
        has_mistake = st.checkbox(
            "Is trade has mistake?",
            value=data.get("estimation") == 0,
            key=f"{state_key}_has_mistake",
        )
        data["estimation"] = 0 if has_mistake else 1
        return data
