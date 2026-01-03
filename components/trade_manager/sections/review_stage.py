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
        st.markdown(
            """<p style=\"font-size:0.875rem;margin: 0;\">Trade estimation</p>
            <p style=\"color: #1f2a3ab3;font-size:0.875rem;margin-bottom: 0.25rem;\">Does this trade fit your trading system?</p>""",
            unsafe_allow_html=True)
        data["estimation"] = st.feedback(
            "thumbs",
            default=data.get("estimation"),
            key=f"{state_key}_estimation"
        )
        data["cold_thoughts"] = st.text_area(
            "Cold thoughts",
            height=120,
            value=data["cold_thoughts"],
            key=f"{state_key}_cold_thoughts"
        )
        return data
