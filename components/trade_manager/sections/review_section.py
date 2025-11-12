"""Блок Review."""

from typing import Any, Dict, Optional

import streamlit as st


def render_review_stage(
    *,
    trade_key: str,
    visible: bool,
    expanded: bool,
    defaults: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Показывает блок Review, если он нужен для текущего статуса."""
    if not visible:
        return None

    with st.expander("Trade review", expanded=expanded):
        cold_thoughts_value = st.text_area(
            "Cold thoughts",
            height=120,
            value=defaults["cold_thoughts"],
            key=f"tm_cold_{trade_key}",
        )
        estimation_default = defaults.get("estimation")
        feedback_kwargs: Dict[str, Any] = {}
        if estimation_default in (0, 1):
            feedback_kwargs["default"] = int(estimation_default)

        estimation_value = st.feedback(
            "thumbs",
            key=f"tm_estimation_{trade_key}",
            **feedback_kwargs,
        )
        normalized_estimation = estimation_value if estimation_value in (0, 1) else None
        return {
            "cold_thoughts": cold_thoughts_value,
            "estimation": normalized_estimation,
        }
