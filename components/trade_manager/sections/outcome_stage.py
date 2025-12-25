"""Блок Outcome."""

from typing import Any, Dict, Optional, Callable
import streamlit as st
from config import TRADE_RESULT_VALUES
from helpers import safe_choice_index


def render_outcome_stage(
    *,
    visible: bool,
    expanded: bool,
    defaults: Dict[str, Any],
    state_key: str,
    on_change: Optional[Callable[[], None]] = None,
) -> Optional[Dict[str, Any]]:
    """Рисует секцию Outcome и возвращает введённые значения."""
    data = defaults.copy()
    if not visible:
        return None

    with st.expander("Outcome", expanded=expanded):
        cc1, cc2 = st.columns(2)
        data["result"] = cc1.selectbox(
            "Result",
            TRADE_RESULT_VALUES,
            placeholder="- Not set -",
            key=f"{state_key}_result",
            index=safe_choice_index(TRADE_RESULT_VALUES, data["result"]),
            on_change=on_change,
        )
        is_miss = str(data["result"]).lower() == "miss"
        data["net_pnl"] = cc2.number_input(
            "Net PnL, $",
            value=data.get(
                "net_pnl") if f"{state_key}_net_pnl" not in st.session_state else None,
            key=f"{state_key}_net_pnl",
            step=1.0,
            disabled=(not data["result"]) or is_miss,
            on_change=on_change,
        )
        cc3, cc4 = st.columns(2)
        data["risk_reward"] = cc3.number_input(
            "R:R",
            value=data.get(
                "risk_reward") if f"{state_key}_risk_reward" not in st.session_state else None,
            key=f"{state_key}_risk_reward",
            step=0.1,
            format="%.2f",
            disabled=not is_miss,
            on_change=on_change,
        )
        data["reward_percent"] = cc4.number_input(
            "Reward, %",
            value=data.get(
                "reward_percent") if f"{state_key}_reward_percent" not in st.session_state else None,
            key=f"{state_key}_reward_percent",
            step=0.1,
            format="%.2f",
            disabled=True,
        )
        data["hot_thoughts"] = st.text_area(
            "Hot thoughts",
            height=100,
            value=data["hot_thoughts"],
            key=f"{state_key}_hot_thoughts",
        )
        st.markdown(
            """<p style=\"font-size:0.875rem;margin: 0;\">Trade estimation</p>
            <p style=\"color: #1f2a3ab3;font-size:0.875rem;margin-bottom: 0.25rem;\">Does this trade fit your trading system?</p>""",
            unsafe_allow_html=True)
        data["estimation"] = st.feedback(
            "thumbs",
            default=data.get("estimation"),
            key=f"{state_key}_estimation"
        )
    return data
