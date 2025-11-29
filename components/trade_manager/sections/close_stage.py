"""Блок After close."""

from typing import Any, Dict, List, Tuple
import streamlit as st
from config import TRADE_RESULT_VALUES


def render_close_stage(
    *,
    visible: bool,
    expanded: bool,
    defaults: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    """Рисует секцию Close и возвращает введённые значения."""
    data = defaults.copy()
    if not visible:
        return data

    with st.expander("After close", expanded=expanded):
        cc1, cc2 = st.columns(2)
        data["result"] = cc1.selectbox(
            "Result",
            TRADE_RESULT_VALUES,
            placeholder="- Not set -",
            index=TRADE_RESULT_VALUES.index(
                data["result"]) if data["result"] else None,
        )
        data["net_pnl"] = cc2.number_input(
            "Net PnL, $",
            value=float(data["net_pnl"]),
            step=1.0,
        )
        data["risk_reward"] = cc1.number_input(
            "R:R",
            value=float(data["risk_reward"]),
            step=0.1,
        )
        data["reward_percent"] = cc2.number_input(
            "Reward %",
            value=float(data["reward_percent"]),
            step=0.5,
        )

        data["hot_thoughts"] = st.text_area(
            "Hot thoughts",
            height=100,
            value=data["hot_thoughts"],
        )
    return data
