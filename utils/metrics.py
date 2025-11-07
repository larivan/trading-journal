# utils/metrics.py — расчёт ключевых метрик и подготовка данных
from typing import Dict, Any
import pandas as pd
import numpy as np


def compute_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty:
        return {
            "count": 0,
            "winrate": 0.0,
            "profit_factor": 0.0,
            "expectancy_r": 0.0,
            "avg_r": 0.0,
            "total_pnl": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0
        }

    # Преобразуем логическую модель в R:
    # Profit -> R = rr
    # Loss   -> R = -1
    # B/e    -> R = 0
    r = np.where(df["trade_result"] == "Profit", df["rr"],
                 np.where(df["trade_result"] == "Loss", -1.0, 0.0))
    df = df.copy()
    df["R"] = r

    total_pnl = float(df["pnl"].sum())
    wins = df[df["pnl"] > 0]["pnl"].sum()
    losses = -df[df["pnl"] < 0]["pnl"].sum()  # модуль
    profit_factor = float(
        wins / losses) if losses > 0 else float("inf") if wins > 0 else 0.0

    winrate = float((df["trade_result"] == "Profit").mean() * 100.0)
    avg_win_r = df[df["R"] > 0]["R"].mean() if (df["R"] > 0).any() else 0.0
    avg_loss_r = -df[df["R"] < 0]["R"].mean() if (df["R"] < 0).any() else 0.0
    expectancy_r = (winrate/100.0) * avg_win_r - \
        (1 - winrate/100.0) * avg_loss_r

    return {
        "count": int(len(df)),
        "winrate": round(winrate, 2),
        "profit_factor": round(profit_factor, 2) if np.isfinite(profit_factor) else float("inf"),
        "expectancy_r": round(expectancy_r, 3),
        "avg_r": round(df["R"].mean(), 3),
        "total_pnl": round(total_pnl, 2),
        "best_trade": round(df["pnl"].max(), 2),
        "worst_trade": round(df["pnl"].min(), 2),
    }


def equity_curve(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    tmp = df.sort_values(["trade_date", "created_at"]).copy()
    tmp["cum_pnl"] = tmp["pnl"].cumsum()
    return tmp[["trade_date", "created_at", "cum_pnl"]]
