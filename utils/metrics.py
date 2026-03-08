# utils/metrics.py — расчёт ключевых метрик для dashboard и других страниц
"""
Unified metrics calculation module.
All trading metrics are calculated here and reused across dashboard and other pages.
"""
from typing import Any, Dict, Optional
import pandas as pd
import numpy as np
from helpers import is_win_rr


def compute_overview_metrics(
    df: pd.DataFrame,
    *,
    fact_df: Optional[pd.DataFrame] = None,
    missed_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Compute overview KPI metrics from trades DataFrame.
    
    Args:
        df: Full trades DataFrame (must have: is_missed, net_pnl, is_correct,
            fact_bias, daily_bias, reward_percent)
        fact_df: Optional pre-filtered executed trades (is_missed=0)
        missed_df: Optional pre-filtered missed trades (is_missed=1)
    
    Returns:
        Dict with keys: fact_count, missed_count, total_count, bias_winrate,
        fact_winrate, potential_winrate, missed_rate, quality_ratio
    """
    if df.empty:
        return {
            "fact_count": 0,
            "missed_count": 0,
            "total_count": 0,
            "bias_winrate": 0.0,
            "fact_winrate": 0.0,
            "potential_winrate": 0.0,
            "missed_rate": 0.0,
            "quality_ratio": 0.0,
        }
    
    # Prepare subsets if not provided
    if fact_df is None:
        fact_df = df[df["is_missed"] == 0].copy()
    if missed_df is None:
        missed_df = df[df["is_missed"] == 1].copy()
    
    total = len(df)
    fact_count = len(fact_df)
    missed_count = len(missed_df)
    
    # Bias winrate: how often daily_bias matched fact_bias
    if total and "fact_bias" in df.columns and "daily_bias" in df.columns:
        bias_winrate = (df["fact_bias"] == df["daily_bias"]).mean()
    else:
        bias_winrate = 0.0

    # Fact winrate: winning trades among executed
    if "risk_reward" in fact_df.columns:
        fact_wins = fact_df[fact_df["risk_reward"].map(is_win_rr)]
    else:
        fact_wins = fact_df.iloc[:0]
    fact_winrate = len(fact_wins) / fact_count if fact_count else 0.0

    # Potential winrate: (fact wins + missed wins) / total
    if "risk_reward" in missed_df.columns:
        miss_wins = missed_df[missed_df["risk_reward"].map(is_win_rr)]
    else:
        miss_wins = missed_df.iloc[:0]
    potential_winrate = (len(fact_wins) + len(miss_wins)) / total if total else 0.0

    # Missed rate
    missed_rate = missed_count / total if total else 0.0

    # Quality ratio: trades with is_correct=1 (no mistake)
    if "is_correct" in df.columns:
        quality_ratio = len(df[df["is_correct"] == 1]) / total if total else 0.0
    else:
        quality_ratio = 0.0
    
    return {
        "fact_count": fact_count,
        "missed_count": missed_count,
        "total_count": total,
        "bias_winrate": bias_winrate,
        "fact_winrate": fact_winrate,
        "potential_winrate": potential_winrate,
        "missed_rate": missed_rate,
        "quality_ratio": quality_ratio,
    }


def compute_risk_metrics(
    fact_df: pd.DataFrame,
    all_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Compute risk, expectancy and PnL metrics from executed trades.
    
    Args:
        fact_df: Executed trades DataFrame (is_missed=0)
                must have: rr (alias for risk_reward), pnl_usd (alias for net_pnl),
                reward_percent
        all_df: Optional full DataFrame for potential calculations
    
    Returns:
        Dict with keys: avg_rr, expected_value, profit_factor, net_pnl,
        total_rr, potential_rr, total_reward, potential_reward, winrate
    """
    if fact_df.empty:
        return {
            "avg_rr": 0.0,
            "expected_value": 0.0,
            "profit_factor": 0.0,
            "net_pnl": 0.0,
            "total_rr": 0.0,
            "potential_rr": 0.0,
            "total_reward": 0.0,
            "potential_reward": 0.0,
            "winrate": 0.0,
        }
    
    # Get RR series (support both old 'rr' alias and 'risk_reward' column)
    if "rr" in fact_df.columns:
        fact_rr = fact_df["rr"]
    elif "risk_reward" in fact_df.columns:
        fact_rr = fact_df["risk_reward"]
    else:
        fact_rr = pd.Series(dtype=float)
    
    # Get PnL series (support both 'pnl_usd' alias and 'net_pnl' column)
    if "pnl_usd" in fact_df.columns:
        fact_pnl = fact_df["pnl_usd"]
    elif "net_pnl" in fact_df.columns:
        fact_pnl = fact_df["net_pnl"]
    else:
        fact_pnl = pd.Series(dtype=float)
    
    # Basic calculations
    avg_rr = float(fact_rr.mean()) if len(fact_rr) else 0.0
    total_rr = float(fact_rr.sum()) if len(fact_rr) else 0.0
    net_pnl = float(fact_pnl.sum()) if len(fact_pnl) else 0.0
    
    # Winrate — only based on risk_reward, never fallback to PnL
    if "risk_reward" in fact_df.columns:
        fact_wins = fact_df[fact_df["risk_reward"].map(is_win_rr)]
    else:
        fact_wins = fact_df.iloc[:0]

    winrate = len(fact_wins) / max(len(fact_df), 1)
    
    # Expected value (EV) in R
    avg_win = float(fact_rr[fact_rr > 0].mean()) if (fact_rr > 0).any() else 0.0
    avg_loss = float(fact_rr[fact_rr < 0].mean()) if (fact_rr < 0).any() else 0.0
    expected_value = winrate * avg_win + (1 - winrate) * avg_loss
    
    # Profit factor
    gross_profit = float(fact_pnl[fact_pnl > 0].sum()) if (fact_pnl > 0).any() else 0.0
    gross_loss = abs(float(fact_pnl[fact_pnl < 0].sum())) if (fact_pnl < 0).any() else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf if gross_profit > 0 else 0.0
    
    # Reward calculations
    total_reward = float(fact_df["reward_percent"].sum()) if "reward_percent" in fact_df.columns and len(fact_df) else 0.0
    
    # Potential calculations (from all trades)
    if all_df is not None and len(all_df):
        if "rr" in all_df.columns:
            potential_rr = float(all_df["rr"].sum())
        elif "risk_reward" in all_df.columns:
            potential_rr = float(all_df["risk_reward"].sum())
        else:
            potential_rr = 0.0
        
        if "reward_percent" in all_df.columns:
            potential_reward = float(all_df["reward_percent"].sum())
        else:
            potential_reward = 0.0
    else:
        potential_rr = avg_rr
        potential_reward = total_reward
    
    return {
        "avg_rr": avg_rr,
        "expected_value": expected_value,
        "profit_factor": profit_factor if np.isfinite(profit_factor) else float("inf"),
        "net_pnl": net_pnl,
        "total_rr": total_rr,
        "potential_rr": potential_rr,
        "total_reward": total_reward,
        "potential_reward": potential_reward,
        "winrate": winrate,
    }


def compute_equity_curve(
    fact_df: pd.DataFrame,
    group_by: str = "date",
) -> pd.DataFrame:
    """
    Compute equity curve data from executed trades.
    
    Args:
        fact_df: Executed trades with date and numeric columns
        group_by: Column to group by ('date' for daily aggregation)
    
    Returns:
        DataFrame with day, rr_sum, pnl_sum, reward_sum, cum_rr, cum_pnl, cum_pct
    """
    if fact_df.empty:
        return pd.DataFrame()
    
    # Get the date column
    if "date" in fact_df.columns:
        date_col = "date"
    elif "date_local" in fact_df.columns:
        date_col = "date_local"
    else:
        return pd.DataFrame()
    
    # Ensure we have required columns
    if "rr" in fact_df.columns:
        rr_col = "rr"
    elif "risk_reward" in fact_df.columns:
        rr_col = "risk_reward"
    else:
        return pd.DataFrame()

    if "pnl_usd" in fact_df.columns:
        pnl_col = "pnl_usd"
    elif "net_pnl" in fact_df.columns:
        pnl_col = "net_pnl"
    else:
        return pd.DataFrame()

    df = fact_df.copy()
    df["date"] = pd.to_datetime(df[date_col])
    if "reward_percent" not in df.columns:
        df["reward_percent"] = 0.0

    daily = (
        df.groupby(df["date"].dt.date)
        .agg(
            rr_sum=(rr_col, "sum"),
            pnl_sum=(pnl_col, "sum"),
            reward_sum=("reward_percent", "sum"),
        )
        .reset_index()
        .rename(columns={"date": "day"})
    )
    daily["day"] = pd.to_datetime(daily["day"])
    daily = daily.sort_values("day")
    
    daily["cum_rr"] = daily["rr_sum"].cumsum()
    daily["cum_pnl"] = daily["pnl_sum"].cumsum()
    daily["cum_pct"] = daily["reward_sum"].cumsum()
    
    return daily
