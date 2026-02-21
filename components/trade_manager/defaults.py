"""Общие дефолтные значения для трейд-менеджера"""

from typing import Any, Dict
import streamlit as st
from helpers import parse_date, parse_time
from config import TM_DEFAULT_PREFIX, ASSETS_VALUES


def get_trade_defaults(
    trade: Dict[str, Any],
    accounts: Dict[int, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Возвращает дефолтные значения"""
    return {
        "state": trade.get("state") or "Open",
        "open": {
            "is_missed": trade.get("is_missed", 0),
            "date": parse_date(trade.get("date_local")),
            "time": parse_time(trade.get("time_local")),
            "account": trade.get("account_id") or accounts[0]["value"] if accounts else None,
            "asset": trade.get("asset"),
            "analysis": _get_session_default("analysis") or trade.get("analysis_id"),
            "setup": trade.get("setup_id"),
            "risk_pct": float(trade.get("risk_pct") or 1.0),
        },
        "outcome": {
            "net_pnl": float(trade.get("net_pnl") or 0.0),
            "risk_reward": float(trade.get("risk_reward") or 0.0),
            "reward_percent": float(trade.get("reward_percent") or 0.0),
            "hot_thoughts": trade.get("hot_thoughts") or "",
        },
        "review": {
            "cold_thoughts": trade.get("cold_thoughts") or "",
            "estimation": trade.get("estimation"),
        },
    }


def _get_session_default(name) -> Any:
    return st.session_state.get(f"{TM_DEFAULT_PREFIX}{name}", None)
