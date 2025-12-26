# app_dashboard_skeleton.py
# Streamlit skeleton for Trading Journal Dashboard (v12+)
# Requirements:
#   streamlit >= 1.25 (for container(border=True) - if not available, remove border=True)
#   pandas, numpy, altair
#
# Run:
#   streamlit run app_dashboard_skeleton.py

import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

# ----------------------------
# Page config
# ----------------------------
st.set_page_config(
    page_title="Dashboard",
    page_icon=":material/bar_chart:",
    layout="wide",
)

# Optional: keep charts readable in wide layout
alt.data_transformers.disable_max_rows()

# ----------------------------
# Mock data (replace with DB later)
# ----------------------------


@st.cache_data
def make_mock_trades(seed: int = 42, n_trades: int = 180) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # Dates spanning ~60 days
    dates = pd.date_range("2025-11-01", periods=60, freq="D")
    trade_dates = rng.choice(dates, size=n_trades, replace=True)

    assets = np.array(["EURUSD", "GBPUSD", "XAUUSD", "XAGUSD", "US100"])
    sessions = np.array(["LoKZ", "NYKZ", "Out of OTT"])
    setups = np.array(
        ["POI → confirmation", "Lq → confirmation", "POI → trend continuation"])

    risk_allowed = np.array([0.5, 1.0, 2.0])
    # introduce some non-standard risk values
    risk = rng.choice(
        np.concatenate([risk_allowed, np.array([0.6, 0.8, 1.2, 1.8])]),
        size=n_trades,
        replace=True,
        p=[0.23, 0.48, 0.14, 0.04, 0.04, 0.03, 0.04],
    )

    # Base "edge" by setup (just for demo)
    setup_edge = {
        "POI → confirmation": 0.15,
        "Lq → confirmation": 0.20,
        "POI → trend continuation": 0.08,
    }
    edge = np.array([setup_edge[s]
                    for s in rng.choice(setups, size=n_trades, replace=True)])

    # Simulate RR distribution: mixture around -1 and +2..+4
    # win probability slightly boosted by setup
    win = rng.random(n_trades) < (0.48 + edge)
    rr = np.where(
        win,
        rng.normal(loc=2.2, scale=1.0, size=n_trades),
        rng.normal(loc=-1.05, scale=0.35, size=n_trades),
    )
    rr = np.clip(rr, -4.0, 7.0)

    # PnL: assume account balance ~10k and risk% as percent of balance per trade
    # PnL($) ≈ rr * (risk%/100) * balance
    balance = 10_000
    pnl = rr * (risk / 100.0) * balance

    df = pd.DataFrame(
        {
            "date": pd.to_datetime(trade_dates),
            "asset": rng.choice(assets, size=n_trades, replace=True),
            "session": rng.choice(sessions, size=n_trades, replace=True),
            "setup": rng.choice(setups, size=n_trades, replace=True),
            "direction": rng.choice(["Long", "Short"], size=n_trades, replace=True),
            "trade_type": rng.choice(["Intraday", "Swing"], size=n_trades, replace=True, p=[0.78, 0.22]),
            "risk_pct": risk,
            "rr": rr,
            "pnl_usd": pnl,
            "is_fact": rng.random(n_trades) < 0.78,  # executed trades
        }
    )

    # Missed opportunities table is usually separate; here we model as non-fact rows
    return df


@st.cache_data
def make_mock_psychology(seed: int = 123) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2025-11-01", periods=60, freq="D")

    # Mock daily psychology metrics
    per = np.clip(rng.normal(loc=10, scale=4, size=len(dates)),
                  0, 30)      # Premature Exit Rate
    emr = np.clip(rng.normal(loc=86, scale=6, size=len(dates)),
                  55, 100)    # Emotional Management Rate
    fei = np.clip(rng.normal(loc=12, scale=8, size=len(
        dates)), -20, 40)    # Fear Efficiency Index

    return pd.DataFrame({"date": dates, "PER": per, "EMR": emr, "FEI": fei})


@st.cache_data
def make_mock_observations(seed: int = 321) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    obs = [
        "NYKZ continuation after macro news",
        "London fakeouts around daily open",
        "Asian range before NY expansion",
        "Trend day: first pullback continuation",
        "Liquidity sweep + quick reversal",
        "Range day: mean reversion works best",
    ]
    occurrences = rng.integers(3, 14, size=len(obs))
    linked_trades = np.clip(
        occurrences - rng.integers(0, 4, size=len(obs)), 0, None)

    # OOR: relative frequency (mock) — for now normalize by total occurrences
    oor = occurrences / occurrences.sum() * 100.0

    status = [
        "Candidate to formalize into rules.",
        "Keep observing; not stable yet.",
        "Needs more samples.",
        "Strong pattern; define filters.",
        "Rare but impactful; isolate conditions.",
        "Moderate; depends on volatility.",
    ]
    df = pd.DataFrame(
        {
            "Observation": obs,
            "Occurrences (#)": occurrences,
            "Linked trades (#)": linked_trades,
            "OOR (%)": oor.round(1),
            "Comment": status,
        }
    ).sort_values("OOR (%)", ascending=False)

    return df


df = make_mock_trades()
psy = make_mock_psychology()
obs_df = make_mock_observations()

# ----------------------------
# Helpers
# ----------------------------


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


def kpi_badge_text(value: float, lo: float = None, hi: float = None, gt: float = None) -> str:
    """
    Produces a Streamlit-friendly delta string like "within KPI" / "below KPI" / "above KPI".
    """
    if gt is not None:
        return "within KPI" if value > gt else "below KPI"
    if lo is not None and hi is not None:
        if lo <= value <= hi:
            return "within KPI"
        return "below KPI" if value < lo else "above KPI"
    return ""


# ----------------------------
# Sidebar filters (skeleton)
# ----------------------------

with st.sidebar:
    st.header("Filters")

    # Date range filter
    min_d = df["date"].min().date()
    max_d = df["date"].max().date()
    date_range = st.date_input("Date range", value=(
        min_d, max_d), min_value=min_d, max_value=max_d)

    account = st.selectbox("Account", [
                           "FP Evaluation #1 (USD)", "FP Funded #1 (USD)", "Demo swing (EUR)"], index=0)
    apply_filters = st.button(
        "Apply filters", type="primary", width="stretch")

# Apply filters immediately (button is just visual parity with your HTML)
dff = df.copy()

# Date filter
if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
    dff = dff[(dff["date"].dt.date >= start) & (dff["date"].dt.date <= end)]

# ----------------------------
# Header
# ----------------------------
st.title("Dashboard")
st.caption(
    "Analytics based on trades, psychology and observations (Streamlit skeleton).")

# ----------------------------
# Overview (with Sample size warning)
# ----------------------------
fact = dff[dff["is_fact"]].copy()
missed = dff[~dff["is_fact"]].copy()
bias_winrate = 0.64
fact_winrate = (fact["rr"] > 0).mean() if len(fact) else 0.0
potential_winrate = (dff["rr"] > 0).mean() if len(dff) else 0.0
missed_rate = (len(missed) / max(len(dff), 1))
triumph_ratio = 0.83
with st.container(border=True):
    st.subheader("Overview")
    st.markdown("""
        <style>
            .trade-summary {
                margin-bottom: 16px;
            }
            .trade-summary-item {
                color: #4b5563;
                display: inline-block;
                padding: 0 20px;
                border: 1px solid #e5e7eb;
                border-radius: 999px;
            }
            .trade-summary-item b {
                color: #111827;
            }
        </style>
        <div class="trade-summary">
            <span class="trade-summary-item"><b>32</b> fact trades</span>
            <span class="trade-summary-item"><b>12</b> missed trades</span>
            <span class="trade-summary-item"><b>44</b> total trades</span>
        </div>
        """, unsafe_allow_html=True)

    # Sample size warning (you can tune threshold)
    SAMPLE_WARN_N = 20
    if len(fact) < SAMPLE_WARN_N:
        st.warning(
            f"Low sample size: only {len(fact)} executed trades in the current filter. "
            "Winrate / PF / EV may be noisy."
        )

    st.markdown("###### Core decision KPIs")

    k1, k2, k3, k4, k5 = st.columns(5)

    k1.metric("Bias winrate (%)",
              f"{bias_winrate*100:.0f}%", delta="within KPI", border=True)
    k2.metric("Fact winrate (%)",
              f"{fact_winrate*100:.0f}%", delta="slightly above KPI", border=True)
    k3.metric("Potential winrate (%)",
              f"{potential_winrate*100:.0f}%", delta="room to realize", border=True)
    k4.metric("Missed trades (%)",
              f"{missed_rate*100:.0f}%", delta="needs work", border=True)
    k5.metric("Triumph ratio (%)",
              f"{triumph_ratio*100:.0f}%", delta="solid", border=True)

# ----------------------------
# Risk, expectancy & PnL (Metrics left 2 cols, Charts right 3 cols)
# Includes:
#   - Equity curve Y-axis switch: Cum RR / Cum PnL / Cum %
#   - Distribution switch: RR | PnL $
# ----------------------------
with st.container(border=True):
    st.subheader("Risk, expectancy & PnL")

    # 5-column region (2 for metrics, 3 for charts)
    c1, c2 = st.columns([1, 4])

    # ---- LEFT: 8 metrics split into 4+4 (delta vs no-delta) ----
    # Compute performance metrics from executed trades only (fact)
    fact_rr = fact["rr"]
    fact_pnl = fact["pnl_usd"]

    avg_rr = float(fact_rr.mean()) if len(fact_rr) else 0.0
    winrate = float((fact_rr > 0).mean()) if len(fact_rr) else 0.0
    avg_win = float(fact_rr[fact_rr > 0].mean()) if (
        fact_rr > 0).any() else 0.0
    avg_loss = float(fact_rr[fact_rr <= 0].mean()) if (
        fact_rr <= 0).any() else 0.0
    # simplified placeholder: EV in R/trade often equals mean(R); your logic may differ.
    ev = avg_rr
    gross_profit = float(fact_pnl[fact_pnl > 0].sum()) if (
        fact_pnl > 0).any() else 0.0
    gross_loss = float(-fact_pnl[fact_pnl < 0].sum()
                       ) if (fact_pnl < 0).any() else 0.0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else np.inf
    net_pnl = float(fact_pnl.sum()) if len(fact_pnl) else 0.0

    # Potential metrics (placeholder)
    potential_rr = float(dff["rr"].mean()) if len(dff) else 0.0
    potential_take_rate = 0.68  # placeholder
    fact_pct = (net_pnl / 10_000) * 100.0  # assuming 10k
    potential_pct_of_profit = potential_take_rate * 100.0

    # KPI thresholds (placeholders)
    KPI_AVG_RR_LO, KPI_AVG_RR_HI = 1.9, 2.1
    KPI_EV_GT = 0.0
    KPI_PF_GT = 1.0
    KPI_PNL_GT = 0.0

    # Metrics container spanning first 2 columns
    with c1:
        st.metric("Average RR (R)", f"{avg_rr:.2f}", delta=kpi_badge_text(
            avg_rr, lo=KPI_AVG_RR_LO, hi=KPI_AVG_RR_HI), border=True)
        st.metric("Expected value (EV, R)",
                  f"{ev:+.2f}", delta=("within KPI" if ev > KPI_EV_GT else "below KPI"), border=True)
        st.metric("Profit factor (#)", f"{profit_factor:.2f}" if np.isfinite(
            profit_factor) else "∞", delta=("within KPI" if profit_factor > KPI_PF_GT else "below KPI"), border=True)
        st.metric("Net PnL ($)", f"{net_pnl:,.0f}", delta=(
            "within KPI" if net_pnl > KPI_PNL_GT else "below KPI"), border=True)

    with c2:
        with st.container(border=True, height="stretch"):
            # Equity curve axis switch
            y_axis = st.radio(
                "Equity curve Y-axis",
                ["Cum RR", "Cum PnL", "Cum %"],
                horizontal=True,
                index=0,
                help="Switch what the equity curve represents.",
            )

            # Build daily series from fact trades
            if len(fact):
                daily = (
                    fact.groupby(fact["date"].dt.date)
                    .agg(rr_sum=("rr", "sum"), pnl_sum=("pnl_usd", "sum"))
                    .reset_index()
                    .rename(columns={"date": "day"})
                )
                daily["day"] = pd.to_datetime(daily["day"])
                daily = daily.sort_values("day")

                daily["cum_rr"] = daily["rr_sum"].cumsum()
                daily["cum_pnl"] = daily["pnl_sum"].cumsum()
                daily["cum_pct"] = (daily["cum_pnl"] / 10_000.0) * 100.0

                if y_axis == "Cum RR":
                    series = daily.set_index("day")["cum_rr"]
                    title = "Equity curve (cumulative RR by day)"
                    y_label = "Cumulative RR (R)"
                elif y_axis == "Cum PnL":
                    series = daily.set_index("day")["cum_pnl"]
                    title = "Equity curve (cumulative PnL by day)"
                    y_label = "Cumulative PnL ($)"
                else:
                    series = daily.set_index("day")["cum_pct"]
                    title = "Equity curve (cumulative return % by day)"
                    y_label = "Cumulative return (%)"
            else:
                series = pd.Series(dtype=float)
                title, y_label = "Equity curve", ""

            st.markdown(f"**{title}**")

            if len(series):
                st.line_chart(series, height="stretch")
            else:
                st.info(
                    "No executed trades for equity curve in the current filters.")

    c3, c4 = st.columns([1, 4])
    with c3:
        st.metric("Fact RR (R)", f"{avg_rr:.2f}", border=True)
        st.metric("Potential RR (R)", f"{potential_rr:.2f}", border=True)
        st.metric("Fact % gained (%)", f"{fact_pct:+.2f}%", border=True)
        st.metric("Potential % of profit gained (%)",
                  f"{potential_pct_of_profit:.0f}%", border=True)

    with c4:
        with st.container(border=True, height="stretch"):
            # Distribution switch + better name
            dist_mode = st.radio(
                "Distribution view",
                ["RR (R)", "PnL ($)"],
                horizontal=True,
                index=0,
                help="Switch distribution between RR and money outcome.",
            )

            if dist_mode == "RR (R)":
                dist_title = "Outcome distribution per trade (RR)"
                values = fact_rr.dropna() if len(fact_rr) else pd.Series(dtype=float)
                x_title = "RR (R)"
            else:
                dist_title = "Outcome distribution per trade (PnL $)"
                values = fact_pnl.dropna() if len(fact_pnl) else pd.Series(dtype=float)
                x_title = "PnL ($)"

            st.markdown(f"**{dist_title}**")
            st.caption(
                "X-axis: outcome bins. Y-axis: number of trades in each bin.")

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
                columns={table_df.columns[0]: "Category", "Total_RR": "Total RR"}
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
with st.container(border=True):
    st.subheader("Psychology & behavior")
    st.caption(
        "Skeleton: 3 headline metrics + behavior flags table (default components).")

    # Filter psychology by date range for parity
    psyf = psy.copy()
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
        psyf = psyf[(psyf["date"].dt.date >= start)
                    & (psyf["date"].dt.date <= end)]

    # headline values (use averages for the period)
    per_val = float(psyf["PER"].mean()) if len(psyf) else 0.0
    emr_val = float(psyf["EMR"].mean()) if len(psyf) else 0.0
    fei_val = float(psyf["FEI"].mean()) if len(psyf) else 0.0

    p1, p2, p3 = st.columns(3)
    p1.metric("PER – Premature Exit Rate (%)", f"{per_val:.0f}", delta=kpi_badge_text(
        avg_rr, lo=KPI_AVG_RR_LO, hi=KPI_AVG_RR_HI), border=True)
    p2.metric("EMR – Emotional Management Rate (%)", f"{emr_val:.0f}", delta=kpi_badge_text(
        avg_rr, lo=KPI_AVG_RR_LO, hi=KPI_AVG_RR_HI), border=True)
    p3.metric("FEI – Fear Efficiency Index (%)", f"{fei_val:+.0f}", delta=kpi_badge_text(
        avg_rr, lo=KPI_AVG_RR_LO, hi=KPI_AVG_RR_HI), border=True)

# ============================
# 5) NOTES & OBSERVATIONS (OOR table)
# ============================
with st.container(border=True):
    st.subheader("Notes & observations")
    st.caption(
        "OOR – Observation Occurrence Rate. Per-observation metric (no global OOR).")

    # In real app you’d compute OOR based on filtered date range + scope
    # Here we just show a realistic table layout.
    st.dataframe(obs_df, hide_index=True)

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
        cols = ["date", "asset", "session", "setup", "trade_type",
                "direction", "risk_pct", "rr", "pnl_usd"]
        recent = recent[cols]
        recent = recent.rename(
            columns={
                "risk_pct": "Risk (%)",
                "rr": "RR",
                "pnl_usd": "PnL ($)",
                "trade_quality": "Trade quality",
                "trade_type": "Trade type",
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
                "trade_type": "Trade type",
                "direction": "Direction",
                "Risk (%)": st.column_config.NumberColumn(
                    "Risk (%)", format="%0.2f"),
                "RR": st.column_config.NumberColumn("RR", format="%0.2f"),
                "PnL ($)": st.column_config.NumberColumn(
                    "PnL ($)", format="$0,0.00"),
            }
        )
    else:
        st.info("No trades.")
