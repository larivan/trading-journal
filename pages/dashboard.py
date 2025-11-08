import streamlit as st
import pandas as pd
import plotly.express as px
from db import (
    list_trades
)
from utils.metrics import compute_metrics, equity_curve
from helpers import apply_page_config_from_file

apply_page_config_from_file(__file__)

rows = list_trades(None)
df = pd.DataFrame(rows)
if df.empty:
    st.info("Пока нет сделок по текущим фильтрам.")
else:
    # Метрики
    m = compute_metrics(df)
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Всего сделок", m["count"])
    k2.metric("Win rate", f"{m['winrate']}%")
    k3.metric("Profit Factor", m["profit_factor"])
    k4.metric("Expectancy (R)", m["expectancy_r"])
    k5.metric("Avg R", m["avg_r"])
    k6.metric("Total PnL", m["total_pnl"])

    st.markdown("---")

    # Equity curve
    eq = equity_curve(df)
    if not eq.empty:
        fig_eq = px.line(eq, x="created_at", y="cum_pnl",
                         title="Equity Curve")
        st.plotly_chart(fig_eq, width="stretch")

    c1, c2 = st.columns(2)
    # Распределение по результату дня
    if "day_result" in df.columns and not df.empty:
        fig_day = px.histogram(
            df, x="day_result", title="Результативность торговых дней")
        c1.plotly_chart(fig_day, width="stretch")
    # Распределение по сетапам
    if "setup" in df.columns and not df.empty:
        fig_setup = px.histogram(df, x="setup", title="Сетапы")
        c2.plotly_chart(fig_setup, width="stretch")

    c3, c4 = st.columns(2)
    # По сессиям
    if "session" in df.columns and not df.empty:
        fig_sess = px.histogram(df, x="session", title="Сессии")
        c3.plotly_chart(fig_sess, width="stretch")
    # По daily bias
    if "daily_bias" in df.columns and not df.empty:
        fig_bias = px.histogram(df, x="daily_bias", title="Daily bias")
        c4.plotly_chart(fig_bias, width="stretch")

    # Таблица последних сделок
    st.markdown("---")
    st.subheader("Последние сделки")
    last_cols = ["trade_date", "open_time", "asset", "pnl",
                 "rr", "setup", "trade_result", "trade_status"]
    last_cols = [c for c in last_cols if c in df.columns]
    st.dataframe(
        df.sort_values(["trade_date", "created_at"], ascending=[False, False])[last_cols].head(20),
        width="stretch",
        hide_index=True
    )
