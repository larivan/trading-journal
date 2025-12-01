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

    with st.expander("Trade review", expanded=expanded):
        data["cold_thoughts"] = st.text_area(
            "Cold thoughts",
            height=120,
            value=data["cold_thoughts"],
            key=f"{state_key}_cold_thoughts"
        )
        data["estimation"] = st.feedback(
            "thumbs",
            default=data.get("estimation"),
            key=f"{state_key}_estimation"
        )
        return data
