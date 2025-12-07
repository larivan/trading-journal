"""Блок Outcome."""

from typing import Any, Dict, Optional
import streamlit as st
from config import TRADE_RESULT_VALUES
from helpers import safe_choice_index


def render_outcome_stage(
    *,
    visible: bool,
    expanded: bool,
    defaults: Dict[str, Any],
    state_key: str,
    risk_pct: Optional[float],
    account_balance: Optional[Any],
) -> Optional[Dict[str, Any]]:
    """Рисует секцию Outcome и возвращает введённые значения."""
    data = defaults.copy()
    if not visible:
        return None

    result_key = f"{state_key}_result"
    net_key = f"{state_key}_net_pnl"
    rr_key = f"{state_key}_risk_reward"
    rp_key = f"{state_key}_reward_percent"
    last_calc_key = f"{state_key}_auto_calc_meta"

    st.session_state.setdefault(result_key, data["result"])
    st.session_state.setdefault(net_key, float(data.get("net_pnl") or 0.0))
    st.session_state.setdefault(rr_key, data.get("risk_reward") or 0.0)
    st.session_state.setdefault(rp_key, data.get("reward_percent") or 0.0)

    def _maybe_auto_fill() -> None:
        """Авторасчёт R:R и Reward% при изменении Net PnL/Result/риска (кроме Miss)."""
        result_val = st.session_state.get(result_key)
        net_val = st.session_state.get(net_key)
        last_meta = st.session_state.get(last_calc_key, {})
        last_net = last_meta.get("net_pnl") if isinstance(last_meta, dict) else None
        last_result = last_meta.get("result") if isinstance(last_meta, dict) else None
        last_risk = last_meta.get("risk_pct") if isinstance(last_meta, dict) else None
        is_miss = str(result_val).lower() == "miss"

        risk_changed = risk_pct != last_risk
        net_changed = net_val != last_net

        if is_miss:
            rr_val = st.session_state.get(rr_key)
            try:
                rr_float = float(rr_val)
            except (TypeError, ValueError):
                rr_float = None
            rp_val = None
            if risk_pct is not None and rr_float is not None:
                try:
                    rp_val = float(risk_pct) * rr_float
                except (TypeError, ValueError):
                    rp_val = None
            st.session_state[rp_key] = rp_val if rp_val is not None else 0.0
            st.session_state[last_calc_key] = {
                "net_pnl": net_val,
                "result": result_val,
                "risk_pct": risk_pct,
            }
            return

        if not (net_changed or risk_changed):
            st.session_state[last_calc_key] = {
                "net_pnl": net_val,
                "result": result_val,
                "risk_pct": risk_pct,
            }
            return

        try:
            net_float = float(net_val)
        except (TypeError, ValueError):
            st.session_state[last_calc_key] = {
                "net_pnl": net_val,
                "result": result_val,
                "risk_pct": risk_pct,
            }
            return

        try:
            balance = float(account_balance) if account_balance is not None else None
        except (TypeError, ValueError):
            balance = None

        reward_percent = None
        if balance not in (None, 0):
            reward_percent = (net_float / balance) * 100

        risk_amount = None
        if balance not in (None, 0) and risk_pct not in (None, 0):
            try:
                risk_amount = balance * float(risk_pct) / 100
            except (TypeError, ValueError):
                risk_amount = None

        risk_reward = (net_float / risk_amount) if risk_amount else None

        if risk_reward is not None:
            st.session_state[rr_key] = risk_reward
        if reward_percent is not None:
            st.session_state[rp_key] = reward_percent
        st.session_state[last_calc_key] = {
            "net_pnl": net_val,
            "result": result_val,
            "risk_pct": risk_pct,
        }

    with st.expander("Outcome", expanded=expanded):
        cc1, cc2 = st.columns(2)
        data["result"] = cc1.selectbox(
            "Result",
            TRADE_RESULT_VALUES,
            placeholder="- Not set -",
            key=result_key,
            index=safe_choice_index(TRADE_RESULT_VALUES, data["result"]),
        )
        result_val = st.session_state.get(result_key)
        is_miss = str(result_val).lower() == "miss"
        net_disabled = (not result_val) or is_miss
        data["net_pnl"] = cc2.number_input(
            "Net PnL, $",
            value=float(st.session_state.get(net_key) or 0.0),
            key=net_key,
            step=1.0,
            disabled=net_disabled,
        )

        _maybe_auto_fill()

        cc3, cc4 = st.columns(2)
        data["risk_reward"] = cc3.number_input(
            "R:R",
            value=float(st.session_state.get(rr_key) or 0.0),
            key=rr_key,
            step=0.1,
            format="%.2f",
            disabled=not is_miss,
        )
        data["reward_percent"] = cc4.number_input(
            "Reward, %",
            value=float(st.session_state.get(rp_key) or 0.0),
            key=rp_key,
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
    return data
