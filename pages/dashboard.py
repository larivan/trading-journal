import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from typing import Dict, Any, Optional
from datetime import date, timedelta
from helpers import (
    to_option_format,
    custom_selectbox
)
from db import (
    list_trades,
    list_analysis,
    list_accounts,
    list_notes,
)

# ----------------------------
# Mock data (replace with DB later)
# ----------------------------

PERIOD_TABS: Dict[str, str] = {
    "today": "Today",
    "week": "Current week",
    "month": "Current month",
    "quarter": "Current quarter",
    "year": "Current year",
    "custom": "Custom",
}

OVERVIEW_KPIS = {
    "bias_winrate": (0.6, 0.75),
    "fact_winrate": (0.55, 0.7),
    "potential_winrate": (0.7, 0.85),
    "missed_rate": (0.0, 0.1),
    "quality_ratio": (0.7, 0.9),
}

RISK_EXPECTANCY_KPIS = {
    "avg_rr": (1.9, 2.1),
    "expected_value": (0.0, None),
    "profit_factor": (1.0, None),
}


def prepare_trades_df() -> pd.DataFrame:
    trades = list_trades()
    analyses = list_analysis()

    if not trades:
        return pd.DataFrame()

    a_df = pd.DataFrame(analyses)
    t_df = pd.DataFrame(trades)

    if not a_df.empty:
        t_df = t_df.merge(
            a_df[["id", "daily_bias", "fact_bias"]],
            left_on="analysis_id",
            right_on="id",
            how="left"
        )

    t_df = t_df[t_df["state"] == "Reviewed"]
    t_df["date"] = pd.to_datetime(t_df["date_local"])
    t_df["rr"] = t_df["risk_reward"].astype(float)
    t_df["pnl_usd"] = t_df["net_pnl"].astype(int)
    t_df["setup"] = t_df["setup_id"].fillna("No setup")

    return t_df


def prepare_observations_df() -> pd.DataFrame:
    obs = list_notes()

    if not obs:
        return pd.DataFrame()

    return pd.DataFrame(obs)

# ----------------------------
# Helpers
# ----------------------------


def kpi_badge(
    options: Dict[str, Any],
    key: str,
    value: float,
    positive_direction: str,
    below_text: str = "Below KPI",
    within_text: str = "Within KPI",
    above_text: str = "Above KPI",
    color=None,
    arrow=None
):
    """
    Produces a delta string.
    """
    lo, hi = options.get(key, (None, None))

    # Если обе переменные None
    if lo is None and hi is None:
        delta = "Invalid Range"
        delta_color = "off"
        delta_arrow = "off"
    else:
        if lo is not None and hi is not None:  # Обе переменные заданы
            if lo <= value <= hi:
                delta = within_text
                delta_color = "normal"
                delta_arrow = "off"
            elif value < lo:
                delta = below_text
                if positive_direction == "higher":
                    delta_color = "inverse"
                    delta_arrow = "down"
                else:
                    delta_color = "normal"
                    delta_arrow = "up"
            else:  # value > hi
                delta = above_text
                if positive_direction == "higher":
                    delta_color = "normal"
                    delta_arrow = "up"
                else:
                    delta_color = "inverse"
                    delta_arrow = "down"
        elif lo is not None:  # Задана только переменная lo
            if value < lo:
                delta = below_text
                if positive_direction == "higher":
                    delta_color = "inverse"
                    delta_arrow = "down"
                else:
                    delta_color = "normal"
                    delta_arrow = "up"
            else:  # value >= lo
                delta = above_text
                if positive_direction == "higher":
                    delta_color = "normal"
                    delta_arrow = "up"
                else:
                    delta_color = "inverse"
                    delta_arrow = "down"
        elif hi is not None:  # Задана только переменная hi
            if value > hi:
                delta = above_text
                if positive_direction == "higher":
                    delta_color = "normal"
                    delta_arrow = "up"
                else:
                    delta_color = "inverse"
                    delta_arrow = "down"
            else:  # value <= hi
                delta = below_text
                if positive_direction == "higher":
                    delta_color = "inverse"
                    delta_arrow = "down"
                else:
                    delta_color = "normal"
                    delta_arrow = "up"

    # Используем переданные значения для цвета и стрелки, если они есть
    delta_color = color or delta_color
    delta_arrow = arrow or delta_arrow

    return {"delta": delta, "delta_color": delta_color, "delta_arrow": delta_arrow}


def total_rr_bar(df_grouped: pd.DataFrame, category_col: str, value_col: str = "Total RR") -> alt.Chart:
    """
    Horizontal bar chart sorted by Total RR (desc) with fixed height.
    """
    # fixed height scales with rows (but with a max to keep it stable)
    rows = len(df_grouped)
    height = min(260, 28 * rows + 40)

    chart = (
        alt.Chart(df_grouped)
        .mark_bar()
        .encode(
            y=alt.Y(f"{category_col}:N", sort="-x", title=None),
            x=alt.X(f"{value_col}:Q", title=value_col),
            tooltip=[category_col, value_col],
        )
        .properties(height=height)
    )
    return chart


# ----------------------------
# Page config
# ----------------------------
st.set_page_config(
    page_title="Dashboard",
    page_icon=":material/bar_chart:",
    layout="wide",
)

# ---------------------------
# Load data
# ----------------------------
data_df = prepare_trades_df()
# psy = prepare_psychology_df()
obs_df = prepare_observations_df()

# ----------------------------
# Header
# ----------------------------
st.title("Dashboard")
st.caption(
    "Analytics based on trades, psychology and observations.")


# Optional: keep charts readable in wide layout
alt.data_transformers.disable_max_rows()

# ----------------------------
# Filters
# ----------------------------

# --- Загружаем список счетов и настраиваем state для форм ---
accounts = to_option_format(
    list_accounts(include_archived=True),
    formatter=lambda acc: f"{acc['name']}",
)

if not accounts:
    st.warning("No accounts found. Please add an account first.")
    st.stop()

period_col, date_col, account_col = st.columns(
    [0.5, 0.25, 0.25], vertical_alignment="bottom"
)
with period_col:
    period_key = "dashboard_period_label"
    if not st.session_state.get(period_key):
        st.session_state[period_key] = "Current quarter"
    selected_label = st.segmented_control(
        "Период",
        options=PERIOD_TABS.values(),
        key=period_key,
        width="stretch",
    )

with account_col:
    account = custom_selectbox(
        "Account",
        accounts,
        value=accounts[0].get("value"),
        key="dashboard_account_filter",
    )


# === ПРИМЕНЕНИЕ ПЕРИОДОВ И КАСТОМНЫХ ФИЛЬТРОВ ===
date_range: Optional[date] = None
label_to_key = {label: key for key, label in PERIOD_TABS.items()}
selected_key = label_to_key.get(selected_label, "quarter")

if selected_key == "custom":
    date_range = date_col.date_input(
        "Date range",
        value=(
            date.today() - timedelta(days=7),
            date.today()
        ),
        format="DD.MM.YYYY",
    )
else:
    today = date.today()
    if selected_key == "today":
        date_range = (today, today)
    elif selected_key == "week":
        date_range = (today - timedelta(days=today.weekday()), today)
    elif selected_key == "month":
        date_range = (today.replace(day=1), today)
    elif selected_key == "quarter":
        quarter = (today.month - 1) // 3
        quarter_start_month = quarter * 3 + 1
        date_range = (today.replace(month=quarter_start_month, day=1), today)
    elif selected_key == "year":
        date_range = (today.replace(month=1, day=1), today)

# Apply filters
if date_range:
    if len(date_range) < 2:
        date_range = (date_range[0], date.today())
    data_df = data_df[(data_df["date"].dt.date >= date_range[0]) & (
        data_df["date"].dt.date <= date_range[1])]
if account:
    data_df = data_df[data_df["account_id"] == account]

if data_df.empty:
    st.warning("No trades found for the selected filters.")
    st.stop()

# ----------------------------
# Overview (with Sample size warning)
# ----------------------------
fact = data_df[data_df["result"].isin(["Win", "Loss", "BE"])].copy()
missed = data_df[data_df["result"] == "Miss"].copy()
bias_winrate = (data_df["fact_bias"] ==
                data_df["daily_bias"]).mean() if len(data_df) else 0.0
# Fact winrate calculation
fact_wins = fact[fact["result"] == "Win"]
fact_winrate = (len(fact_wins) / max(len(fact), 1)) if len(fact) else 0.0
# Potential winrate calculation
miss_trades = data_df[data_df["result"] == "Miss"]
miss_win_trades = miss_trades[miss_trades["reward_percent"] > 0]
potential_winrate = (len(fact_wins) + len(miss_win_trades)) / \
    max(len(data_df), 1) if len(data_df) else 0.0

missed_rate = (len(missed) / max(len(data_df), 1)) if len(data_df) else 0.0
quality_ratio = (len(data_df[data_df["estimation"] == 1]) /
                 max(len(data_df), 1)) if len(data_df) else 0.0

with st.container(border=True):
    st.subheader("Overview")
    st.markdown(f"""
        <style>
            .trade-summary {{
                margin-bottom: 16px;
            }}
            .trade-summary-item {{
                color: #4b5563;
                display: inline-block;
                padding: 0 20px;
                border: 1px solid #e5e7eb;
                border-radius: 999px;
            }}
            .trade-summary-item b {{
                color: #111827;
            }}
        </style>
        <div class="trade-summary">
            <span class="trade-summary-item"><b>{len(fact)}</b> fact trades</span>
            <span class="trade-summary-item"><b>{len(missed)}</b> missed trades</span>
            <span class="trade-summary-item"><b>{len(data_df)}</b> total trades</span>
        </div>
        """, unsafe_allow_html=True)

    # Sample size warning (you can tune threshold)
    SAMPLE_WARN_N = 20
    if len(fact) < SAMPLE_WARN_N:
        st.warning(
            f"Low sample size: only {len(fact)} executed trades in the current filter. "
            "Metrics may be noisy."
        )

    st.markdown("###### Core decision KPIs")

    k1, k2, k3, k4, k5 = st.columns(5)

    k1.metric(
        "Bias winrate",
        f"{bias_winrate*100:.0f}%",
        border=True,
        **kpi_badge(OVERVIEW_KPIS, "bias_winrate", bias_winrate, positive_direction="higher"),
    )
    k2.metric(
        "Fact winrate",
        f"{fact_winrate*100:.0f}%",
        **kpi_badge(OVERVIEW_KPIS, "fact_winrate", fact_winrate, positive_direction="higher"),
        border=True
    )
    k3.metric(
        "Potential winrate",
        f"{potential_winrate*100:.0f}%",
        **kpi_badge(OVERVIEW_KPIS, "potential_winrate", potential_winrate, positive_direction="higher"),
        border=True
    )
    k4.metric(
        "Missed trades",
        f"{missed_rate*100:.0f}%",
        **kpi_badge(OVERVIEW_KPIS, "missed_rate", missed_rate, positive_direction="lower"),
        border=True
    )
    k5.metric(
        "Execution Quality Ratio",
        f"{quality_ratio*100:.0f}%",
        **kpi_badge(OVERVIEW_KPIS, "quality_ratio", quality_ratio, positive_direction="higher"),
        border=True
    )

# ----------------------------
# Risk, expectancy & PnL (Metrics left 2 cols, Charts right 3 cols)
# Includes:
#   - Equity curve Y-axis switch: Cum RR / Cum PnL / Cum %
#   - Distribution switch: RR | PnL $
# ----------------------------
with st.container(border=True):
    st.subheader("Risk, expectancy & PnL")

    c1, c2 = st.columns([1, 4])
    # Avg RR calculation
    fact_rr = fact["rr"]
    avg_rr = float(fact_rr.mean()) if len(fact_rr) else 0.0
    # Expected value (EV) calculation
    avg_win = float(fact_rr[fact_rr > 0].mean()) if (
        fact_rr > 0).any() else 0.0
    avg_loss = float(fact_rr[fact_rr < 0].mean()) if (
        fact_rr < 0).any() else 0.0
    expected_value = fact_winrate * avg_win + (1 - fact_winrate) * avg_loss
    # Profit factor calculation
    fact_pnl = fact["pnl_usd"]
    gross_profit = float(fact_pnl[fact_pnl > 0].sum()) if (
        fact_pnl > 0).any() else 0.0
    gross_loss = abs(float(fact_pnl[fact_pnl < 0].sum())) if (
        fact_pnl < 0).any() else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else np.inf
    # Net PnL calculation
    net_pnl = float(fact_pnl.sum()) if len(fact_pnl) else 0.0
    # Total RR calculation
    total_rr = float(fact_rr.sum()) if len(fact_rr) else 0.0
    # Potential RR calculation
    potential_rr = float(data_df["rr"].mean()) if len(data_df) else 0.0
    # Total reward calculation
    total_reward = float(fact["reward_percent"].sum()) if len(fact) else 0.0
    # Potential reward calculation
    potential_reward = float(
        data_df["reward_percent"].sum()) if len(data_df) else 0.0

    # Metrics container spanning first 2 columns
    with c1:
        st.metric(
            "Average RR",
            f"{avg_rr:.2f}R",
            **kpi_badge(
                RISK_EXPECTANCY_KPIS,
                "avg_rr",
                avg_rr,
                positive_direction="higher"
            ),
            border=True
        )
        st.metric(
            "Expected value",
            f"{expected_value:+.2f}R",
            **kpi_badge(
                RISK_EXPECTANCY_KPIS,
                "expected_value",
                expected_value,
                positive_direction="higher"
            ),
            border=True
        )
        st.metric(
            "Profit factor",
            f"{profit_factor:.2f}" if np.isfinite(profit_factor) else "∞",
            **kpi_badge(
                RISK_EXPECTANCY_KPIS,
                "profit_factor",
                profit_factor,
                positive_direction="higher"
            ),
            border=True
        )
        st.metric(
            "Net PnL",
            f"{net_pnl:,.0f}$",
            border=True
        )

    with c2:
        with st.container(border=True, height="stretch"):
            st.markdown(f"**Equity curve**")

            # Equity curve axis switch
            y_key = "dashboard_y_axis_label"
            if not st.session_state.get(y_key):
                st.session_state[y_key] = "Cumulative %"
            y_axis = st.segmented_control(
                "Equity curve Y-axis",
                key=y_key,
                options=["Cumulative %", "Cumulative RR", "Cumulative $"],
                label_visibility="collapsed",
            )

            # Build daily series from fact trades
            if len(fact):
                daily = (
                    fact.groupby(fact["date"].dt.date)
                    .agg(rr_sum=("rr", "sum"), pnl_sum=("pnl_usd", "sum"), reward_sum=("reward_percent", "sum"))
                    .reset_index()
                    .rename(columns={"date": "day"})
                )
                daily["day"] = pd.to_datetime(daily["day"])
                daily = daily.sort_values("day")

                daily["cum_rr"] = daily["rr_sum"].cumsum()
                daily["cum_pnl"] = daily["pnl_sum"].cumsum()
                daily["cum_pct"] = daily["reward_sum"].cumsum()

                if y_axis == "Cumulative RR":
                    series = daily.set_index("day")["cum_rr"]
                elif y_axis == "Cumulative $":
                    series = daily.set_index("day")["cum_pnl"]
                else:
                    series = daily.set_index("day")["cum_pct"]
            else:
                series = pd.Series(dtype=float)

            if len(series):
                st.line_chart(series, height="stretch")
            else:
                st.info(
                    "No executed trades for equity curve in the current filters.")

    c3, c4 = st.columns([1, 4])
    with c3:
        st.metric("Total fact RR", f"{total_rr:.2f}R", border=True)
        st.metric("Total potential RR", f"{potential_rr:.2f}R", border=True)
        st.metric("Total fact reward", f"{total_reward:+.2f}%", border=True)
        st.metric("Total potential reward",
                  f"{potential_reward:.0f}%", border=True)

    with c4:
        with st.container(border=True, height="stretch"):
            st.markdown(f"**Outcome distribution per trade**")
            # Distribution switch
            dist_mode_key = "dashboard_dist_mode_label"
            if not st.session_state.get(dist_mode_key):
                st.session_state[dist_mode_key] = "RR (R)"
            dist_mode = st.segmented_control(
                "Distribution view",
                key=dist_mode_key,
                options=["RR (R)", "PnL ($)"],
                label_visibility="collapsed",
            )

            if dist_mode == "RR (R)":
                values = fact_rr.dropna() if len(fact_rr) else pd.Series(dtype=float)
                x_title = "RR (R)"
            else:
                values = fact_pnl.dropna() if len(fact_pnl) else pd.Series(dtype=float)
                x_title = "PnL ($)"

            if len(values):
                dist_df = pd.DataFrame({x_title: values})

                # Altair histogram
                hist = (
                    alt.Chart(dist_df)
                    .mark_bar()
                    .encode(
                        x=alt.X(f"{x_title}:Q", bin=alt.Bin(
                            maxbins=24), title=x_title),
                        y=alt.Y("count():Q", title="Trades"),
                        tooltip=[alt.Tooltip("count():Q", title="Trades")],
                    )
                    .properties(height=220)
                )
                st.altair_chart(hist, height="stretch")
            else:
                st.info(
                    "No executed trades for distribution in the current filters.")

# ============================
# 3) BREAKDOWNS BY ASSET / SESSION / SETUP
# table (left) + Total RR bar chart (right)
# ============================
with st.container(border=True):
    st.subheader("Breakdowns by asset, session, setup")
    st.caption(
        "Each block: table on the left, Total RR bar chart on the right. Sorted by Total RR.")

    def breakdown_block(title: str, group_col: str):
        st.markdown(f"#### {title}")

        # Use executed trades for performance breakdowns
        if len(fact) == 0:
            st.info("No executed trades in the current filters.")
            return

        g = (
            fact.groupby(group_col)
            .agg(
                Trades=("rr", "size"),
                Winrate=("rr", lambda s: (s > 0).mean() * 100.0),
                Avg_RR=("rr", "mean"),
                Total_RR=("rr", "sum"),
            )
            .reset_index()
            .rename(columns={group_col: title[:-1] if title.endswith("s") else title})
        )

        # Sort by Total RR desc
        g = g.sort_values("Total_RR", ascending=False)

        # Table formatting (keep as dataframe for skeleton)
        table_df = g.copy()
        table_df["Winrate"] = table_df["Winrate"].round(1)
        table_df["Avg_RR"] = table_df["Avg_RR"].round(2)
        table_df["Total_RR"] = table_df["Total_RR"].round(2)

        left, right = st.columns([2.2, 1.2])

        with left:
            st.dataframe(
                table_df[[table_df.columns[0], "Trades", "Winrate", "Avg_RR"]],
                use_container_width=True,
                hide_index=True,
            )

        with right:
            # Bar chart (Total RR)
            bar_df = table_df[[table_df.columns[0], "Total_RR"]].rename(
                columns={table_df.columns[0]                         : "Category", "Total_RR": "Total RR"}
            )
            chart = total_rr_bar(
                bar_df, category_col="Category", value_col="Total RR")
            st.altair_chart(chart, height="stretch")

    breakdown_block("Assets", "asset")
    st.divider()
    breakdown_block("Sessions", "session")
    st.divider()
    breakdown_block("Setups", "setup")


# ============================
# 4) PSYCHOLOGY & BEHAVIOR
# PER / EMR / FEI + Behavior flags table
# ============================
# with st.container(border=True):
#     st.subheader("Psychology & behavior")
#     st.caption(
#         "Skeleton: 3 headline metrics + behavior flags table (default components).")

#     # Filter psychology by date range for parity
#     psyf = psy.copy()
#     if isinstance(date_range, tuple) and len(date_range) == 2:
#         start, end = date_range
#         psyf = psyf[(psyf["date"].dt.date >= start)
#                     & (psyf["date"].dt.date <= end)]

#     # headline values (use averages for the period)
#     per_val = float(psyf["PER"].mean()) if len(psyf) else 0.0
#     emr_val = float(psyf["EMR"].mean()) if len(psyf) else 0.0
#     fei_val = float(psyf["FEI"].mean()) if len(psyf) else 0.0

#     p1, p2, p3 = st.columns(3)
#     p1.metric("PER – Premature Exit Rate (%)", f"{per_val:.0f}", border=True)
#     p2.metric("EMR – Emotional Management Rate (%)",
#               f"{emr_val:.0f}", border=True)
#     p3.metric("FEI – Fear Efficiency Index (%)",
#               f"{fei_val:+.0f}", border=True)

# ============================
# 5) NOTES & OBSERVATIONS (OOR table)
# ============================
with st.container(border=True):
    st.subheader("Notes & observations")
    st.caption(
        "OOR – Observation Occurrence Rate. Per-observation metric (no global OOR).")

    # In real app you’d compute OOR based on filtered date range + scope
    # Here we just show a realistic table layout.
    st.dataframe(
        obs_df[["title", "body"]],
        column_config={
            "title": "Title",
            "body": "Observation",
            # "OOR": st.column_config.NumberColumn("OOR", format="%0.1f"),
            # "Linked trades": st.column_config.NumberColumn("Linked trades", format="%0.1f"),

        },
        hide_index=True
    )

# ============================
# 6) RECENT TRADES
# ============================
with st.container(border=True):
    st.subheader("Recent trades")
    st.caption(
        "In the real app this is ideal for AgGrid. Here: default dataframe skeleton.")

    if len(fact):
        recent = fact.sort_values("date", ascending=False).head(25).copy()
        recent["date"] = recent["date"].dt.strftime("%Y-%m-%d")
        cols = ["date", "asset", "session",
                "setup", "risk_pct", "rr", "pnl_usd"]
        recent = recent[cols]
        recent = recent.rename(
            columns={
                "risk_pct": "Risk (%)",
                "rr": "RR",
                "pnl_usd": "PnL ($)",
                "trade_quality": "Trade quality",
            }
        )
        st.dataframe(
            recent,
            use_container_width=True,
            hide_index=True,
            column_config={
                "date": st.column_config.DateColumn("Date", format="DD.MM.YYYY"),
                "asset": "Asset",
                "session": "Session",
                "setup": "Setup",
                "Risk (%)": st.column_config.NumberColumn(
                    "Risk (%)", format="%0.1f"),
                "RR": st.column_config.NumberColumn("RR", format="%0.1f"),
                "PnL ($)": st.column_config.NumberColumn(
                    "PnL ($)", format="%0.01f"),
            }
        )
    else:
        st.info("No trades.")
