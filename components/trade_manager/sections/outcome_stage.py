"""Блок Outcome."""

from typing import Any, Dict, Optional, Callable
import streamlit as st


def render_outcome_stage(
    *,
    visible: bool,
    expanded: bool,
    defaults: Dict[str, Any],
    state_key: str,
    is_missed: int,
    on_change: Optional[Callable[[], None]] = None,
) -> Optional[Dict[str, Any]]:
    """Рисует секцию Outcome и возвращает введённые значения."""
    data = defaults.copy()
    if not visible:
        return None

    net_pnl_key = f"{state_key}_net_pnl"
    risk_reward_key = f"{state_key}_risk_reward"
    reward_percent_key = f"{state_key}_reward_percent"

    if net_pnl_key not in st.session_state:
        st.session_state[net_pnl_key] = float(data.get("net_pnl") or 0.0)
    if risk_reward_key not in st.session_state:
        st.session_state[risk_reward_key] = float(data.get("risk_reward") or 0.0)
    if reward_percent_key not in st.session_state:
        st.session_state[reward_percent_key] = float(data.get("reward_percent") or 0.0)

    with st.expander("Outcome", expanded=expanded):
        data["net_pnl"] = st.number_input(
            "Net PnL, $",
            key=net_pnl_key,
            step=0.01,
            format="%.2f",
            disabled=is_missed,
            on_change=on_change,
        )
        cc3, cc4 = st.columns(2)
        data["risk_reward"] = cc3.number_input(
            "R:R",
            key=risk_reward_key,
            step=0.1,
            format="%.2f",
            disabled=not is_missed,
            on_change=on_change,
        )
        data["reward_percent"] = cc4.number_input(
            "Reward, %",
            key=reward_percent_key,
            step=0.1,
            format="%.2f",
            disabled=True,
        )
        data["hot_thoughts"] = st.text_area(
            "Hot thoughts",
            height=120,
            value=data["hot_thoughts"],
            key=f"{state_key}_hot_thoughts",
        )
    return data
