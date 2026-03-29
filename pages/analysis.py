import sqlite3
from datetime import date, timedelta
from utils.date_periods import compute_date_range
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from config import (
    ASSETS_VALUES,
    DAILY_BIAS_VALUES,
    DAY_RESULT_VALUES,
    LOCAL_TZ,
)
from db import add_analysis, delete_analysis, transaction
from utils.cached_data import cached_analysis, filter_analysis, invalidate_analysis, page_mark
from helpers import format_local_date
from utils.auth import get_current_user_id, get_setting

st.set_page_config(page_title="Analysis Database",
                   page_icon=":material/insights:", layout="wide")
st.title(":material/insights: Analysis Database")

user_id = get_current_user_id()
page_mark("analysis", "start")

TAB_DEFINITIONS: Dict[str, str] = {
    "today": "Today",
    "week": "Current week",
    "month": "Current month",
    "quarter": "Current quarter",
    "year": "Current year",
    "custom": "Custom",
}


period_col, _ = st.columns([0.7, 0.3], vertical_alignment="bottom")
with period_col:
    period_key = "analysis_current_period_label"
    if not st.session_state.get(period_key):
        st.session_state[period_key] = "Current month"
    selected_label = st.segmented_control(
        "Period",
        options=TAB_DEFINITIONS.values(),
        key=period_key,
        width="stretch",
    )

filters: Dict[str, Any] = {}
date_range: Optional[Tuple[date, date]] = None
asset_choice: Optional[str] = None

label_to_key = {label: key for key, label in TAB_DEFINITIONS.items()}
selected_key = label_to_key.get(selected_label, "today")

if selected_key == "custom":
    with st.container():
        fc1, fc2, fc3, fc4, fc5 = st.columns(5)
        date_range = fc1.date_input(
            "Date Range",
            value=(
                date.today() - timedelta(days=7),
                date.today()
            ),
            format="DD.MM.YYYY",
        )
        asset_choice = fc2.selectbox("Asset", ["All"] + ASSETS_VALUES)
        daily_bias_choice = fc3.selectbox(
            "Daily bias", ["All"] + DAILY_BIAS_VALUES)
        fact_bias_choice = fc4.selectbox(
            "Fact bias", ["All"] + DAILY_BIAS_VALUES)
        day_result_choice = fc5.selectbox(
            "Result", ["All"] + DAY_RESULT_VALUES)

    if asset_choice != "All":
        filters["asset"] = asset_choice
    if daily_bias_choice != "All":
        filters["daily_bias"] = daily_bias_choice
    if fact_bias_choice != "All":
        filters["fact_bias"] = fact_bias_choice
    if day_result_choice != "All":
        filters["day_result"] = day_result_choice
else:
    local_tz = get_setting("local_tz", LOCAL_TZ)
    date_range = compute_date_range(selected_key, tz_name=local_tz)

if date_range:
    if len(date_range) < 2:
        date_range = (date_range[0], date.today())
    filters["date_from"] = date_range[0].isoformat()
    filters["date_to"] = date_range[1].isoformat()

rows = filter_analysis(cached_analysis(user_id), filters)
page_mark("analysis", "data_loaded")

# === ТАБЛИЦА ===
selected_rows: List[int] = []
if not rows:
    st.info("No analysis found for the selected period.")
else:
    df = pd.DataFrame(rows)
    df["date_display"] = df["date_local"].apply(format_local_date)
    df["_link"] = "/analysis_editor?id=" + df["id"].astype(str)
    df["asset_display"] = df["asset"].apply(
        lambda v: ", ".join(v) if isinstance(v, list) else (v or "")
    )

    display_cols = ["_link", "date_display", "asset_display",
                    "daily_bias", "fact_bias", "day_result"]
    for col in display_cols:
        if col not in df.columns:
            df[col] = None

    event = st.dataframe(
        df[display_cols],
        column_config={
            "date_display": st.column_config.TextColumn("Date"),
            "asset_display": st.column_config.TextColumn("Asset"),
            "daily_bias": st.column_config.TextColumn("Daily bias"),
            "fact_bias": st.column_config.TextColumn("Fact bias"),
            "day_result": st.column_config.TextColumn("Result"),
            "_link": st.column_config.LinkColumn("", display_text="Open →"),
        },
        selection_mode="multi-row",
        on_select="rerun",
        use_container_width=True,
        hide_index=True,
        key=f"analysis_dataframe_{selected_key}",
    )

    selected_rows = event.selection.rows

btn_create, btn_delete, _ = st.columns([0.12, 0.15, 0.73])
assets_list = get_setting("assets", ASSETS_VALUES)
with btn_create.popover("Create", type="primary", width="stretch"):
    filter_asset = asset_choice if (
        selected_key == "custom" and asset_choice not in (None, "All")) else None
    default_ast = (
        filter_asset
        or (get_setting("default_asset") if get_setting("default_asset") in assets_list else None)
        or (assets_list[0] if assets_list else "EUR/USD")
    )
    pop_assets = st.multiselect(
        "Asset", assets_list,
        default=[default_ast] if default_ast in assets_list else [],
        key="_create_analysis_pop_asset",
    )
    if st.button("Go", type="primary", width=250, key="_create_analysis_pop_go"):
        if not pop_assets:
            st.error("Select at least one asset.")
            st.stop()
        with transaction() as conn:
            new_id = add_analysis(user_id, {
                "date_local": date.today().isoformat(),
                "asset": pop_assets,
            }, conn=conn)
        invalidate_analysis()
        st.session_state["_new_analysis_id"] = new_id
        st.session_state["_back_page"] = "pages/analysis.py"
        st.session_state.pop("_back_params", None)
        st.switch_page("pages/analysis_editor.py")
if selected_rows:
    selected_ids = [rows[i]["id"] for i in selected_rows]
    if btn_delete.button(f"Delete ({len(selected_ids)})", type="secondary", width="stretch"):
        st.session_state["_pending_delete_analysis_ids"] = selected_ids
        st.rerun()


@st.dialog("Delete analyses")
def _confirm_delete_analyses(ids: List[Any]) -> None:
    n = len(ids)
    st.warning(
        f"Delete {n} {'analyses' if n > 1 else 'analysis'}? This cannot be undone.")
    col1, col2 = st.columns(2)
    if col1.button("Delete", type="primary", width="stretch"):
        from db import transaction
        try:
            with transaction() as conn:
                for analysis_id in ids:
                    try:
                        delete_analysis(analysis_id, user_id, conn=conn)
                    except (ValueError, sqlite3.Error) as exc:
                        st.toast(
                            f"Failed to delete analysis {analysis_id}: {exc}", icon="❌")
        except Exception as exc:
            st.toast(f"Delete failed: {exc}", icon="❌")
        st.session_state.pop("_pending_delete_analysis_ids", None)
        invalidate_analysis()
        st.rerun()
    if col2.button("Cancel", width="stretch"):
        st.session_state.pop("_pending_delete_analysis_ids", None)
        st.rerun()


pending_delete_ids = st.session_state.get("_pending_delete_analysis_ids")
if pending_delete_ids:
    _confirm_delete_analyses(pending_delete_ids)

page_mark("analysis", "done")
