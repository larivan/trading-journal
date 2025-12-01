"""Блок After close."""

from typing import Any, Dict, List, Tuple
import streamlit as st
from config import TRADE_RESULT_VALUES
from helpers import safe_choice_index


def render_close_stage(
    *,
    visible: bool,
    expanded: bool,
    defaults: Dict[str, Any],
    state_key: str
) -> Tuple[Dict[str, Any], List[str]]:
    """Рисует секцию Close и возвращает введённые значения."""
    data = defaults.copy()
    if not visible:
        return None

    with st.expander("After close", expanded=expanded):
        cc1, cc2 = st.columns(2)
        data["result"] = cc1.selectbox(
            "Result",
            TRADE_RESULT_VALUES,
            placeholder="- Not set -",
            key=f"{state_key}_result",
            index=safe_choice_index(TRADE_RESULT_VALUES, data["result"]),
        )
        data["net_pnl"] = cc2.number_input(
            "Net PnL, $",
            value=float(data["net_pnl"]),
            key=f"{state_key}_net_pnl",
            step=1.0,
        )
        cc3, cc4 = st.columns(2)
        data["risk_reward"] = cc3.number_input(
            "R:R",
            value=float(data["risk_reward"]),
            key=f"{state_key}_risk_reward",
            step=0.1,
        )
        data["reward_percent"] = cc4.number_input(
            "Reward %",
            value=float(data["reward_percent"]),
            key=f"{state_key}_reward_percent",
            step=0.5,
        )

        data["hot_thoughts"] = st.text_area(
            "Hot thoughts",
            height=100,
            value=data["hot_thoughts"],
            key=f"{state_key}_hot_thoughts",
        )
    return data
