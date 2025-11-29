"""Общие дефолтные значения для трейд-менеджера"""

from typing import Any, Dict

from config import ASSETS
from helpers import parse_date, parse_time, current_option_label


def get_trade_defaults(
    trade: Dict[str, Any],
    accounts,
    analyses,
    setups
) -> Dict[str, Dict[str, Any]]:
    """Возвращает дефолтные значения"""
    return {
        "state": trade.get("state") or "open",
        "open": {
            "date": parse_date(trade.get("date_local")),
            "time": parse_time(trade.get("time_local")),
            "account": current_option_label(accounts, trade.get("account_id")),
            "asset": trade.get("asset"),
            "analysis": current_option_label(analyses, trade.get("analysis_id")),
            "setup": current_option_label(setups, trade.get("setup_id")),
            "risk_pct": float(trade.get("risk_pct") or 1.0),
        },
        "close": {
            "result": trade.get("result"),
            "net_pnl": trade.get("net_pnl") or 0.0,
            "risk_reward": trade.get("risk_reward") or 0.0,
            "reward_percent": trade.get("reward_percent") or 0.0,
            "hot_thoughts": trade.get("hot_thoughts") or "",
        },
        "review": {
            "cold_thoughts": trade.get("cold_thoughts") or "",
            "estimation": trade.get("estimation"),
        },
    }
