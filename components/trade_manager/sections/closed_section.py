"""Блок After close."""

from typing import Any, Dict, List, Tuple

import streamlit as st

from config import EMOTIONAL_PROBLEMS, RESULT_VALUES

from ..constants import RESULT_PLACEHOLDER


def render_closed_stage(
    *,
    trade_key: str,
    visible: bool,
    expanded: bool,
    defaults: Dict[str, Any],
    emotional_defaults: List[str],
) -> Tuple[Dict[str, Any], List[str]]:
    """Рисует секцию After close и возвращает введённые значения."""
    if not visible:
        return {}, emotional_defaults

    with st.expander("After close", expanded=expanded):
        cc1, cc2 = st.columns(2)
        result_options = [RESULT_PLACEHOLDER] + RESULT_VALUES
        result_value = cc1.selectbox(
            "Result",
            result_options,
            index=result_options.index(
                defaults["result"]) if defaults["result"] in result_options else 0,
            key=f"tm_result_{trade_key}",
            format_func=lambda value: (
                value if value == RESULT_PLACEHOLDER else value.replace('_', ' ').title()
            ),
        )
        net_pnl_value = cc2.number_input(
            "Net PnL, $",
            value=float(defaults["net_pnl"]),
            step=1.0,
            key=f"tm_pnl_{trade_key}",
        )
        risk_reward_value = cc1.number_input(
            "R:R",
            value=float(defaults["risk_reward"]),
            step=0.1,
            key=f"tm_rr_{trade_key}",
        )
        reward_percent_value = cc2.number_input(
            "Reward %",
            value=float(defaults["reward_percent"]),
            step=0.5,
            key=f"tm_reward_{trade_key}",
        )

        hot_thoughts_value = st.text_area(
            "Hot thoughts",
            height=100,
            value=defaults["hot_thoughts"],
            key=f"tm_hot_{trade_key}",
        )
        updated_emotions = st.multiselect(
            "Emotional challenges",
            EMOTIONAL_PROBLEMS,
            default=emotional_defaults,
            key=f"tm_emotions_{trade_key}",
        )
        inputs = {
            "result": result_value,
            "net_pnl": net_pnl_value,
            "risk_reward": risk_reward_value,
            "reward_percent": reward_percent_value,
            "hot_thoughts": hot_thoughts_value,
        }
    return inputs, updated_emotions
