
import pytest
import pandas as pd
import numpy as np
from utils.metrics import (
    compute_overview_metrics,
    compute_risk_metrics,
    compute_equity_curve,
)

@pytest.fixture
def sample_trades_df():
    data = [
        # Win (Fact)
        {"is_missed": 0, "net_pnl": 100.0, "risk_reward": 2.0, "fact_bias": "Bullish", "daily_bias": "Bullish", "reward_percent": 1.0, "is_correct": 1, "date_local": "2023-01-01"},
        # Loss (Fact)
        {"is_missed": 0, "net_pnl": -50.0, "risk_reward": -1.0, "fact_bias": "Bearish", "daily_bias": "Bullish", "reward_percent": -1.0, "is_correct": 0, "date_local": "2023-01-01"},
        # Missed Win
        {"is_missed": 1, "net_pnl": 0.0, "risk_reward": 3.0, "fact_bias": "Bullish", "daily_bias": "Bullish", "reward_percent": 3.0, "is_correct": 1, "date_local": "2023-01-02"},
    ]
    return pd.DataFrame(data)

def test_compute_overview_metrics_empty():
    df = pd.DataFrame()
    metrics = compute_overview_metrics(df)
    assert metrics["total_count"] == 0
    assert metrics["fact_winrate"] == 0.0

def test_compute_overview_metrics_basic(sample_trades_df):
    metrics = compute_overview_metrics(sample_trades_df)
    
    # Counts
    assert metrics["total_count"] == 3
    assert metrics["fact_count"] == 2
    assert metrics["missed_count"] == 1
    
    # Winrates
    # Fact: 1 win / 2 trades = 0.5
    assert metrics["fact_winrate"] == 0.5
    
    # Bias: 
    # 1. Bullish == Bullish (Match)
    # 2. Bearish != Bullish (No Match)
    # 3. Bullish == Bullish (Match)
    # 2/3 = 0.666...
    assert metrics["bias_winrate"] == pytest.approx(2/3)
    
    # Potential: (Fact Wins + Missed Wins) / Total
    # Fact Wins: 1, Missed Wins: 1 (reward > 0) -> Total 2
    # 2 / 3 = 0.666...
    assert metrics["potential_winrate"] == pytest.approx(2/3)
    
    # Quality: is_correct=1 count / total
    # 2 liked / 3 total = 0.666...
    assert metrics["quality_ratio"] == pytest.approx(2/3)

def test_compute_risk_metrics_empty():
    df = pd.DataFrame()
    metrics = compute_risk_metrics(df)
    assert metrics["net_pnl"] == 0.0
    assert metrics["profit_factor"] == 0.0

def test_compute_risk_metrics_basic(sample_trades_df):
    fact_df = sample_trades_df[sample_trades_df["is_missed"] == 0]
    metrics = compute_risk_metrics(fact_df, all_df=sample_trades_df)
    
    # PnL: 100 - 50 = 50
    assert metrics["net_pnl"] == 50.0
    
    # Avg RR: (2.0 - 1.0) / 2 = 0.5
    assert metrics["avg_rr"] == 0.5
    
    # Profit factor: 100 / 50 = 2.0
    assert metrics["profit_factor"] == 2.0
    
    # Winrate: 1 win / 2 trades = 0.5
    assert metrics["winrate"] == 0.5
    
    # EV: 0.5 * avg_win + 0.5 * avg_loss
    # avg_win = 2.0, avg_loss = -1.0
    # 0.5 * 2.0 + 0.5 * (-1.0) = 1.0 - 0.5 = 0.5
    assert metrics["expected_value"] == 0.5
    
    # Potential RR (from all_df): (2.0 - 1.0 + 3.0) / 3 = 1.333...
    assert metrics["potential_rr"] == pytest.approx(4/3)

def test_compute_equity_curve(sample_trades_df):
    fact_df = sample_trades_df[sample_trades_df["is_missed"] == 0]
    curve = compute_equity_curve(fact_df, group_by="date")

    assert len(curve) > 0
    # Grouped by date (both are 2023-01-01)
    assert len(curve) == 1

    row = curve.iloc[0]
    assert row["day"] == pd.Timestamp("2023-01-01")
    assert row["pnl_sum"] == 50.0
    assert row["cum_pnl"] == 50.0
    assert row["rr_sum"] == 1.0  # 2.0 - 1.0


# ── compute_overview_metrics — непокрытые ветки ─────────────────────────────

def test_overview_no_bias_columns():
    """Нет fact_bias/daily_bias → bias_winrate == 0."""
    df = pd.DataFrame([
        {"is_missed": 0, "net_pnl": 100.0, "risk_reward": 2.0, "is_correct": 1},
    ])
    metrics = compute_overview_metrics(df)
    assert metrics["bias_winrate"] == 0.0


def test_overview_no_risk_reward_column():
    """Нет колонки risk_reward → fact_winrate == 0."""
    df = pd.DataFrame([
        {"is_missed": 0, "net_pnl": 100.0, "is_correct": 1,
         "fact_bias": "B", "daily_bias": "B"},
    ])
    metrics = compute_overview_metrics(df)
    assert metrics["fact_winrate"] == 0.0


def test_overview_no_is_correct_column():
    """Нет колонки is_correct → quality_ratio == 0."""
    df = pd.DataFrame([
        {"is_missed": 0, "net_pnl": 100.0, "risk_reward": 2.0,
         "fact_bias": "B", "daily_bias": "B"},
    ])
    metrics = compute_overview_metrics(df)
    assert metrics["quality_ratio"] == 0.0


def test_overview_all_missed_no_facts():
    """Все трейды missed → fact_winrate == 0, missed_rate == 1."""
    df = pd.DataFrame([
        {"is_missed": 1, "net_pnl": 0.0, "risk_reward": 2.0,
         "fact_bias": "B", "daily_bias": "B", "is_correct": 1},
    ])
    metrics = compute_overview_metrics(df)
    assert metrics["fact_winrate"] == 0.0
    assert metrics["missed_rate"] == 1.0


# ── compute_risk_metrics — непокрытые ветки ──────────────────────────────────

def test_risk_metrics_rr_alias():
    """Колонка 'rr' вместо 'risk_reward' принимается корректно."""
    df = pd.DataFrame([
        {"rr": 2.0, "net_pnl": 100.0, "reward_percent": 2.0},
        {"rr": -1.0, "net_pnl": -50.0, "reward_percent": -1.0},
    ])
    metrics = compute_risk_metrics(df)
    assert metrics["avg_rr"] == pytest.approx(0.5)
    assert metrics["net_pnl"] == 50.0


def test_risk_metrics_pnl_usd_alias():
    """Колонка 'pnl_usd' вместо 'net_pnl' принимается корректно."""
    df = pd.DataFrame([
        {"risk_reward": 2.0, "pnl_usd": 100.0},
        {"risk_reward": -1.0, "pnl_usd": -50.0},
    ])
    metrics = compute_risk_metrics(df)
    assert metrics["net_pnl"] == 50.0


def test_risk_metrics_no_rr_or_pnl_columns():
    """Нет ни rr, ни pnl колонок → нули вместо ошибок."""
    df = pd.DataFrame([{"is_missed": 0}])
    metrics = compute_risk_metrics(df)
    assert metrics["avg_rr"] == 0.0
    assert metrics["net_pnl"] == 0.0
    assert metrics["winrate"] == 0.0


def test_risk_metrics_no_risk_reward_winrate_is_zero():
    """Нет risk_reward → winrate = 0 (нет fallback через PnL)."""
    df = pd.DataFrame([
        {"net_pnl": 100.0},
        {"net_pnl": -50.0},
    ])
    metrics = compute_risk_metrics(df)
    # Without risk_reward column there's no way to determine wins — winrate = 0
    assert metrics["winrate"] == 0.0


def test_risk_metrics_no_all_df():
    """all_df=None → potential_rr == avg_rr."""
    df = pd.DataFrame([
        {"risk_reward": 2.0, "net_pnl": 100.0},
    ])
    metrics = compute_risk_metrics(df, all_df=None)
    assert metrics["potential_rr"] == metrics["avg_rr"]


def test_risk_metrics_all_wins_infinite_profit_factor():
    """Только прибыльные трейды → profit_factor == inf."""
    df = pd.DataFrame([
        {"risk_reward": 2.0, "net_pnl": 100.0},
    ])
    metrics = compute_risk_metrics(df)
    assert metrics["profit_factor"] == float("inf")


# ── compute_equity_curve — непокрытые ветки ──────────────────────────────────

def test_equity_curve_with_date_column():
    """Колонка 'date' (не 'date_local') принимается корректно."""
    df = pd.DataFrame([
        {"date": "2026-01-01", "risk_reward": 1.5, "net_pnl": 75.0, "reward_percent": 1.5},
    ])
    curve = compute_equity_curve(df)
    assert len(curve) == 1
    assert curve.iloc[0]["pnl_sum"] == 75.0


def test_equity_curve_rr_alias():
    """Колонка 'rr' вместо 'risk_reward' принимается корректно."""
    df = pd.DataFrame([
        {"date_local": "2026-01-01", "rr": 2.0, "net_pnl": 100.0},
    ])
    curve = compute_equity_curve(df)
    assert len(curve) == 1
    assert curve.iloc[0]["rr_sum"] == 2.0


def test_equity_curve_pnl_usd_alias():
    """Колонка 'pnl_usd' вместо 'net_pnl' принимается корректно."""
    df = pd.DataFrame([
        {"date_local": "2026-01-01", "risk_reward": 2.0, "pnl_usd": 100.0},
    ])
    curve = compute_equity_curve(df)
    assert len(curve) == 1
    assert curve.iloc[0]["pnl_sum"] == 100.0


def test_equity_curve_no_date_column():
    """Нет колонки date/date_local → пустой DataFrame."""
    df = pd.DataFrame([{"risk_reward": 2.0, "net_pnl": 100.0}])
    assert compute_equity_curve(df).empty


def test_equity_curve_no_rr_column():
    """Нет колонки rr/risk_reward → пустой DataFrame."""
    df = pd.DataFrame([{"date_local": "2026-01-01", "net_pnl": 100.0}])
    assert compute_equity_curve(df).empty


def test_equity_curve_no_pnl_column():
    """Нет колонки net_pnl/pnl_usd → пустой DataFrame."""
    df = pd.DataFrame([{"date_local": "2026-01-01", "risk_reward": 2.0}])
    assert compute_equity_curve(df).empty


def test_equity_curve_single_trade():
    """Один трейд — cum_pnl == pnl_sum."""
    df = pd.DataFrame([
        {"date_local": "2026-01-01", "risk_reward": 1.0, "net_pnl": 50.0},
    ])
    curve = compute_equity_curve(df)
    assert len(curve) == 1
    assert curve.iloc[0]["cum_pnl"] == 50.0


def test_equity_curve_cumulative_ordering():
    """Несколько дат — cum_pnl нарастает в хронологическом порядке."""
    df = pd.DataFrame([
        {"date_local": "2026-01-03", "risk_reward": -1.0, "net_pnl": -50.0},
        {"date_local": "2026-01-01", "risk_reward": 2.0, "net_pnl": 100.0},
    ])
    curve = compute_equity_curve(df)
    assert len(curve) == 2
    assert curve.iloc[0]["cum_pnl"] == 100.0
    assert curve.iloc[1]["cum_pnl"] == 50.0
