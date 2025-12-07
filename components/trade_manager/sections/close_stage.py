"""Блок After close."""

from typing import Any, Dict, Optional
import streamlit as st
from config import TRADE_RESULT_VALUES
from helpers import safe_choice_index


def render_close_stage(
    *,
    visible: bool,
    expanded: bool,
    defaults: Dict[str, Any],
    state_key: str
) -> Optional[Dict[str, Any]]:
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

        data["hot_thoughts"] = st.text_area(
            "Hot thoughts",
            height=100,
            value=data["hot_thoughts"],
            key=f"{state_key}_hot_thoughts",
        )
    return data
