"""Блок Outcome."""

from typing import Any, Dict, Optional, Callable
import streamlit as st


def render_outcome_stage(
    *,
    defaults: Dict[str, Any],
    state_key: str,
    is_missed: int,
    on_change: Optional[Callable[[], None]] = None,
) -> Dict[str, Any]:
    """Рисует секцию Outcome и возвращает введённые значения."""
    data = defaults.copy()

    net_pnl_key = f"{state_key}_net_pnl"
    risk_reward_key = f"{state_key}_risk_reward"
    reward_percent_key = f"{state_key}_reward_percent"

    if net_pnl_key not in st.session_state:
        st.session_state[net_pnl_key] = float(data.get("net_pnl") or 0.0)
    if risk_reward_key not in st.session_state:
        st.session_state[risk_reward_key] = float(data.get("risk_reward") or 0.0)
    if reward_percent_key not in st.session_state:
        st.session_state[reward_percent_key] = float(data.get("reward_percent") or 0.0)

    if is_missed:
        data["risk_reward"] = st.number_input(
            "R:R",
            key=risk_reward_key,
            step=0.1,
            format="%.2f",
            on_change=on_change,
        )
        data["net_pnl"] = st.session_state.get(net_pnl_key, 0.0)
    else:
        data["net_pnl"] = st.number_input(
            "Net PnL, $",
            key=net_pnl_key,
            step=0.01,
            format="%.2f",
            on_change=on_change,
        )
        data["risk_reward"] = st.session_state.get(risk_reward_key, 0.0)
    data["reward_percent"] = st.session_state.get(reward_percent_key, 0.0)
    return data
