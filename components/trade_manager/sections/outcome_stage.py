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

    with st.expander("Outcome", expanded=expanded):
        data["net_pnl"] = st.number_input(
            "Net PnL, $",
            value=float(data.get("net_pnl") or 0.0),
            key=f"{state_key}_net_pnl",
            step=1.0,
            disabled=is_missed,
            on_change=on_change,
        )
        cc3, cc4 = st.columns(2)
        data["risk_reward"] = cc3.number_input(
            "R:R",
            value=float(data.get("risk_reward") or 0.0),
            key=f"{state_key}_risk_reward",
            step=0.1,
            format="%.2f",
            disabled=not is_missed,
            on_change=on_change,
        )
        data["reward_percent"] = cc4.number_input(
            "Reward, %",
            value=float(data.get("reward_percent") or 0.0),
            key=f"{state_key}_reward_percent",
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
