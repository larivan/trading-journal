"""Общие дефолтные значения для трейд-менеджера"""

from typing import Any, Dict

from config import ASSETS, RESULT_PLACEHOLDER
from helpers import current_option_label, parse_trade_date, parse_trade_time


def build_trade_defaults(
    trade: Dict[str, Any],
    accounts: Dict[str, Any],
    analyses: Dict[str, Any],
    setups: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """Возвращает дефолтные значения"""

    date_value = parse_trade_date(trade.get("date_local"))
    time_value = parse_trade_time(trade.get("time_local"))
    account_label = current_option_label(accounts, trade.get("account_id"))
    analysis_label = current_option_label(analyses, trade.get("analysis_id"))
    setup_label = current_option_label(setups, trade.get("setup_id"))
    asset_candidates = ASSETS or [trade.get("asset") or "—"]
    asset_default = (
        trade.get("asset")
        if trade.get("asset") in asset_candidates
        else asset_candidates[0]
    )
    if asset_default not in asset_candidates:
        asset_candidates = [asset_default] + asset_candidates

    estimation_value = trade.get("estimation")
    if estimation_value not in (0, 1):
        estimation_value = None

    return {
        "open": {
            "date": date_value,
            "time": time_value,
            "account_label": account_label,
            "asset": asset_default,
            "analysis_label": analysis_label,
            "setup_label": setup_label,
            "risk_pct": float(trade.get("risk_pct") or 1.0),
            "asset_options": asset_candidates,
        },
        "closed": {
            "result": trade.get("result") or RESULT_PLACEHOLDER,
            "net_pnl": trade.get("net_pnl") or 0.0,
            "risk_reward": trade.get("risk_reward") or 0.0,
            "reward_percent": trade.get("reward_percent") or 0.0,
            "hot_thoughts": trade.get("hot_thoughts") or "",
            "emotional": trade.get("emotional_problems"),
        },
        "review": {
            "cold_thoughts": trade.get("cold_thoughts") or "",
            "estimation": estimation_value,
        },
    }
