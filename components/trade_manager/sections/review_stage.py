"""Блок Review."""

from typing import Any, Dict, Optional

import streamlit as st


def render_review_stage(
    *,
    visible: bool,
    expanded: bool,
    defaults: Dict[str, Any],
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
        )
        data["estimation"] = st.feedback(
            "thumbs",
            default=data.get("estimation"),
        )
        return data
