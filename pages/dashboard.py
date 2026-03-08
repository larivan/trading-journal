from utils.cached_data import page_mark
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from typing import Dict, Any, Optional, Tuple
from datetime import date, timedelta
from utils.date_periods import compute_date_range
from config import LOCAL_TZ
from helpers import (
    to_option_format,
    custom_selectbox,
    is_win_rr,
)
from utils.cached_data import cached_trades, cached_analysis, cached_accounts, cached_setups
from utils.auth import get_current_user_id, get_setting
from utils.metrics import (
    compute_overview_metrics,
    compute_risk_metrics,
    compute_equity_curve,
    compute_streak,
    compute_max_drawdown_rr,
)

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

user_id = get_current_user_id()


@st.cache_data(ttl=3600)
def prepare_trades_df(user_id: int) -> pd.DataFrame:
    trades = cached_trades(user_id)
    analyses = cached_analysis(user_id)
    setups = cached_setups(user_id)

    if not trades:
        return pd.DataFrame()

    a_df = pd.DataFrame(analyses)
    t_df = pd.DataFrame(trades)

    if not a_df.empty:
        t_df["analysis_id"] = pd.to_numeric(
            t_df["analysis_id"], errors="coerce")
        t_df = t_df.merge(
            a_df[["id", "daily_bias", "fact_bias"]],
            left_on="analysis_id",
            right_on="id",
            how="left"
        )

    t_df = t_df[t_df["is_correct"].notna()]
    t_df["date"] = pd.to_datetime(t_df["date_local"])
    t_df["rr"] = pd.to_numeric(t_df["risk_reward"], errors="coerce")
    t_df["pnl_usd"] = pd.to_numeric(
        t_df["net_pnl"], errors="coerce").fillna(0.0)

    if setups:
        setup_map = {s["id"]: s["name"] for s in setups}
        t_df["setup"] = t_df["setup_id"].map(setup_map).fillna("No setup")
    else:
        t_df["setup"] = t_df["setup_id"].fillna("No setup")

    return t_df


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
    lo, hi = options.get(key, (None, None))

    if lo is None and hi is None:
        delta = "Invalid Range"
        delta_color = "off"
        delta_arrow = "off"
    else:
        if lo is not None and hi is not None:
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
            else:
                delta = above_text
                if positive_direction == "higher":
                    delta_color = "normal"
                    delta_arrow = "up"
                else:
                    delta_color = "inverse"
                    delta_arrow = "down"
        elif lo is not None:
            if value < lo:
                delta = below_text
                if positive_direction == "higher":
                    delta_color = "inverse"
                    delta_arrow = "down"
                else:
                    delta_color = "normal"
                    delta_arrow = "up"
            else:
                delta = above_text
                if positive_direction == "higher":
                    delta_color = "normal"
                    delta_arrow = "up"
                else:
                    delta_color = "inverse"
                    delta_arrow = "down"
        elif hi is not None:
            if value > hi:
                delta = above_text
                if positive_direction == "higher":
                    delta_color = "normal"
                    delta_arrow = "up"
                else:
                    delta_color = "inverse"
                    delta_arrow = "down"
            else:
                delta = below_text
                if positive_direction == "higher":
                    delta_color = "inverse"
                    delta_arrow = "down"
                else:
                    delta_color = "normal"
                    delta_arrow = "up"

    delta_color = color or delta_color
    delta_arrow = arrow or delta_arrow

    return {"delta": delta, "delta_color": delta_color, "delta_arrow": delta_arrow}


def total_rr_bar(df_grouped: pd.DataFrame, category_col: str, value_col: str = "Total RR") -> alt.Chart:
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


def _equity_altair_chart(daily: pd.DataFrame, y_col: str, y_label: str) -> alt.Chart:
    df = daily[["day", y_col]].copy()
    df["zero"] = 0.0
    df["y_pos"] = df[y_col].clip(lower=0)
    df["y_neg"] = df[y_col].clip(upper=0)
    base = alt.Chart(df).encode(x=alt.X("day:T", title=None))
    area_pos = base.mark_area(opacity=0.2, color="#22c55e").encode(
        y=alt.Y("y_pos:Q", title=y_label), y2=alt.Y2("zero:Q"))
    area_neg = base.mark_area(opacity=0.2, color="#ef4444").encode(
        y=alt.Y("zero:Q"), y2=alt.Y2("y_neg:Q"))
    line = base.mark_line(color="#3b82f6", strokeWidth=2).encode(
        y=alt.Y(f"{y_col}:Q"),
        tooltip=[
            alt.Tooltip("day:T", title="Date", format="%d %b %Y"),
            alt.Tooltip(f"{y_col}:Q", title=y_label, format=".2f"),
        ])
    zero_rule = alt.Chart(pd.DataFrame({"y": [0.0]})).mark_rule(
        color="#9ca3af", strokeDash=[4, 2]).encode(y="y:Q")
    return (area_pos + area_neg + line + zero_rule).properties(height=280)


_DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_DAY_MAP = {0: "Mon", 1: "Tue", 2: "Wed",
            3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}


def _calendar_heatmap(fact_df: pd.DataFrame) -> Optional[alt.Chart]:
    if fact_df.empty:
        return None
    df = fact_df.copy()
    df["tdate"] = pd.to_datetime(df["date"]).dt.normalize()
    daily = (
        df.groupby("tdate")
        .agg(daily_rr=("rr", "sum"), trades=("rr", "count"))
        .reset_index()
    )

    # Expand to full weeks (Mon→Sun) so all 7 rows always appear
    d_min = daily["tdate"].min()
    d_max = daily["tdate"].max()
    d_min = d_min - pd.Timedelta(days=d_min.dayofweek)       # back to Monday
    # forward to Sunday
    d_max = d_max + pd.Timedelta(days=6 - d_max.dayofweek)
    all_days = pd.DataFrame({"tdate": pd.date_range(d_min, d_max, freq="D")})
    daily = all_days.merge(daily, on="tdate", how="left")
    daily["daily_rr"] = daily["daily_rr"].fillna(0.0)
    daily["trades"] = daily["trades"].fillna(0).astype(int)

    daily["day_label"] = daily["tdate"].dt.dayofweek.map(_DAY_MAP)
    daily["week"] = (
        daily["tdate"] - pd.to_timedelta(daily["tdate"].dt.dayofweek, unit="d")
    ).dt.strftime("%Y-%m-%d")

    # Vega expression: show month name only on the first week of each month
    month_expr = (
        "parseInt(slice(datum.value, 8, 10)) <= 7"
        " ? timeFormat(toDate(datum.value), '%b')"
        " : ''"
    )

    return (
        alt.Chart(daily)
        .mark_rect(stroke="white", strokeWidth=2)
        .encode(
            x=alt.X(
                "week:O",
                sort="ascending",
                title=None,
                axis=alt.Axis(
                    labelExpr=month_expr,
                    labelAngle=0,
                    labelFontSize=11,
                    ticks=False,
                ),
            ),
            y=alt.Y("day_label:O", sort=_DAY_ORDER, title=None,
                    axis=alt.Axis(labelFontSize=11, ticks=False)),
            color=alt.condition(
                "datum.trades > 0",
                alt.Color(
                    "daily_rr:Q",
                    scale=alt.Scale(domainMid=0, scheme="redyellowgreen"),
                    legend=None,
                ),
                alt.value("#e5e7eb"),
            ),
            tooltip=[
                alt.Tooltip("tdate:T", title="Date", format="%d %b %Y"),
                alt.Tooltip("daily_rr:Q", title="Daily RR", format="+.2f"),
                alt.Tooltip("trades:Q", title="Trades"),
            ],
        )
        .properties(height=280)
    )


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
page_mark("dashboard", "start")
data_df = prepare_trades_df(user_id)
page_mark("dashboard", "data_loaded")

# ----------------------------
# Header
# ----------------------------
st.title("Dashboard")
st.caption(
    "Analytics based on reviewed trades only.")

alt.data_transformers.disable_max_rows()

# ----------------------------
# Filters
# ----------------------------
accounts = to_option_format(
    cached_accounts(user_id, True),
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
    if period_key not in st.session_state:
        st.session_state[period_key] = "Current quarter"
    selected_label = st.segmented_control(
        "Period",
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
date_range: Optional[Tuple[date, date]] = None
label_to_key = {label: key for key, label in PERIOD_TABS.items()}
selected_key = label_to_key.get(selected_label, "quarter")

if selected_key == "custom":
    date_range = date_col.date_input(
        "Date Range",
        value=(
            date.today() - timedelta(days=7),
            date.today()
        ),
        format="DD.MM.YYYY",
    )
else:
    local_tz = get_setting("local_tz", LOCAL_TZ)
    date_range = compute_date_range(selected_key, tz_name=local_tz)

if data_df.empty:
    st.warning("No reviewed trades found.")
    st.stop()

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
# Compute metrics
# ----------------------------
fact = data_df[data_df["is_missed"] == 0].copy()
missed = data_df[data_df["is_missed"] == 1].copy()

overview = compute_overview_metrics(data_df, fact_df=fact, missed_df=missed)
fact_winrate = overview["fact_winrate"]
potential_winrate = overview["potential_winrate"]
bias_winrate = overview["bias_winrate"]
missed_rate = overview["missed_rate"]
quality_ratio = overview["quality_ratio"]

risk = compute_risk_metrics(fact, all_df=data_df)
avg_rr = risk["avg_rr"]
expected_value = risk["expected_value"]
profit_factor = risk["profit_factor"]
net_pnl = risk["net_pnl"]
total_rr = risk["total_rr"]
potential_rr = risk["potential_rr"]

fact_rr = fact["rr"] if len(fact) else pd.Series(dtype=float)
fact_pnl = fact["pnl_usd"] if len(fact) else pd.Series(dtype=float)
best_rr = float(fact_rr.max()) if len(fact) else 0.0
worst_rr = float(fact_rr.min()) if len(fact) else 0.0
max_drawdown = compute_max_drawdown_rr(fact)
streak_n, streak_d = compute_streak(fact)

# Trade summary + sample warning
st.caption(
    f"**{len(fact)}** fact · **{len(missed)}** missed · **{len(data_df)}** total")
if len(fact) < 20:
    st.warning(
        f"Low sample size: only {len(fact)} executed trades in the current filter. "
        "Metrics may be noisy."
    )

# ----------------------------
# Hero strip
# ----------------------------
h1, h2, h3, h4, h5 = st.columns(5)

h1.metric(
    "Fact winrate",
    f"{fact_winrate*100:.0f}%" if fact_winrate is not None else "—",
    help="% of executed trades that closed as wins (RR > 0.05)",
    **kpi_badge(OVERVIEW_KPIS, "fact_winrate", fact_winrate or 0.0, positive_direction="higher"),
    border=True,
)
h2.metric(
    "Expected value",
    f"{expected_value:+.2f}R",
    help="Win rate × avg win + loss rate × avg loss",
    **kpi_badge(RISK_EXPECTANCY_KPIS, "expected_value", expected_value, positive_direction="higher"),
    border=True,
)
h3.metric(
    "Net PnL",
    f"{net_pnl:,.0f}$",
    delta="Profit" if net_pnl >= 0 else "Loss",
    delta_color="normal" if net_pnl >= 0 else "inverse",
    delta_arrow="off",
    border=True,
)
h4.metric(
    "Max Drawdown",
    f"{max_drawdown:.2f}R",
    help="Largest peak-to-trough decline in cumulative RR",
    border=True,
    height="stretch"
)
if streak_d == "W":
    streak_delta, streak_delta_color = "Win streak", "normal"
elif streak_d == "L":
    streak_delta, streak_delta_color = "Loss streak", "inverse"
else:
    streak_delta, streak_delta_color = None, "off"
h5.metric(
    "Streak",
    f"{streak_n} {streak_d}" if streak_d != "—" else "—",
    delta=streak_delta,
    delta_color=streak_delta_color,
    delta_arrow="off",
    help="Current consecutive win/loss streak",
    border=True,
)

# ----------------------------
# Charts: equity curve + calendar
# ----------------------------
with st.container(border=True):
    chart_left, chart_right = st.columns([3, 2], gap="medium")

    with chart_left:
        st.markdown("**Equity curve**")
        y_key = "dashboard_equity_y_axis"
        if y_key not in st.session_state:
            st.session_state[y_key] = "Cumulative RR"
        y_axis = st.segmented_control(
            "Equity Y-axis",
            key=y_key,
            options=["Cumulative RR", "Cumulative $"],
            label_visibility="collapsed",
        )
        if len(fact):
            daily = compute_equity_curve(fact)
            if not daily.empty:
                y_col, y_label = ("cum_pnl", "Cumulative $") if y_axis == "Cumulative $" else (
                    "cum_rr", "Cumulative RR")
                st.altair_chart(_equity_altair_chart(
                    daily, y_col, y_label), height="stretch")
            else:
                st.info(
                    "No executed trades for equity curve in the current filters.")
        else:
            st.info("No executed trades for equity curve in the current filters.")

    with chart_right:
        st.markdown("**Daily performance calendar**")
        cal = _calendar_heatmap(fact)
        if cal is not None:
            st.caption(
                "Color: daily cumulative RR. Green = positive, red = negative.")
            st.altair_chart(cal, height="stretch")
        else:
            st.info("No executed trades for calendar in the current filters.")

# ----------------------------
# Advanced metrics
# ----------------------------
with st.expander("Advanced metrics"):
    a1, a2, a3, a4, a5 = st.columns(5)
    a1.metric(
        "Average RR",
        f"{avg_rr:.2f}R",
        **kpi_badge(RISK_EXPECTANCY_KPIS, "avg_rr", avg_rr, positive_direction="higher"),
        border=True,
    )
    a2.metric(
        "Profit factor",
        f"{profit_factor:.2f}" if np.isfinite(profit_factor) else "∞",
        **kpi_badge(RISK_EXPECTANCY_KPIS, "profit_factor", profit_factor, positive_direction="higher"),
        border=True,
    )
    a3.metric("Total RR", f"{total_rr:.2f}R", border=True, height="stretch")
    a4.metric("Potential RR", f"{potential_rr:.2f}R",
              border=True, height="stretch")
    a5.metric("Best Trade", f"{best_rr:+.2f}R", border=True, height="stretch")

    b1, b2, b3, b4, b5 = st.columns(5)
    b1.metric(
        "Bias winrate",
        f"{bias_winrate*100:.0f}%",
        help="% of days where your daily bias matched the actual market direction",
        **kpi_badge(OVERVIEW_KPIS, "bias_winrate", bias_winrate, positive_direction="higher"),
        border=True,
    )
    b2.metric(
        "Potential winrate",
        f"{potential_winrate*100:.0f}%",
        help="% of all trades (fact + missed) that were winners",
        **kpi_badge(OVERVIEW_KPIS, "potential_winrate", potential_winrate, positive_direction="higher"),
        border=True,
    )
    b3.metric(
        "Missed trades",
        f"{missed_rate*100:.0f}%",
        help="% of your setups you identified but didn't execute",
        **kpi_badge(OVERVIEW_KPIS, "missed_rate", missed_rate, positive_direction="lower"),
        border=True,
    )
    b4.metric(
        "Quality ratio",
        f"{quality_ratio*100:.0f}%",
        help="% of trades executed without process mistakes",
        **kpi_badge(OVERVIEW_KPIS, "quality_ratio", quality_ratio, positive_direction="higher"),
        border=True,
    )
    b5.metric("Worst Trade", f"{worst_rr:+.2f}R",
              border=True, height="stretch")

# ============================
# Breakdowns
# ============================
with st.container(border=True):
    st.subheader("Breakdowns")

    def breakdown_block(title: str, group_col: str):
        if len(fact) == 0:
            st.info("No executed trades in the current filters.")
            return

        g = (
            fact.groupby(group_col)
            .agg(
                Trades=("rr", "size"),
                Winrate=("rr", lambda s: s.map(is_win_rr).mean() * 100.0),
                Avg_RR=("rr", "mean"),
                Total_RR=("rr", "sum"),
            )
            .reset_index()
            .rename(columns={group_col: title[:-1] if title.endswith("s") else title})
        )

        g = g.sort_values("Total_RR", ascending=False)
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
            bar_df = table_df[[table_df.columns[0], "Total_RR"]].rename(
                columns={table_df.columns[0]
                    : "Category", "Total_RR": "Total RR"}
            )
            chart = total_rr_bar(
                bar_df, category_col="Category", value_col="Total RR")
            st.altair_chart(chart, height="stretch")

    tab1, tab2, tab3 = st.tabs(["Assets", "Sessions", "Setups"])
    with tab1:
        breakdown_block("Assets", "asset")
    with tab2:
        breakdown_block("Sessions", "session")
    with tab3:
        breakdown_block("Setups", "setup")


page_mark("dashboard", "done")
