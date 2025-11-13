from typing import Optional, Tuple

import pandas as pd
import streamlit as st


def render_analysis_table(
    rows,
    tab_key: str,
) -> Tuple[bool, Optional[int]]:
    if not rows:
        st.info("Нет анализов для выбранного периода.")
        return False, None

    df = pd.DataFrame(rows)
    display_columns = [
        "date_local",
        "asset",
        "day_result",
        "pre_market_summary",
        "plan_summary",
        "post_market_summary",
    ]
    table = df[display_columns].rename(columns={
        "date_local": "Дата",
        "asset": "Инструмент",
        "day_result": "Day result",
        "pre_market_summary": "Pre-market",
        "plan_summary": "Plan",
        "post_market_summary": "Post",
    })
    table["Дата"] = pd.to_datetime(table["Дата"], errors="coerce")
    if "time_local" in df.columns:
        table.insert(
            1,
            "Время",
            pd.to_datetime(df["time_local"], errors="coerce").dt.time,
        )

    table_key = f"analysis_table_{tab_key}"
    st.dataframe(
        table,
        key=table_key,
        hide_index=True,
        on_select="rerun",
        selection_mode=["single-row"],
        column_config={
            "Дата": st.column_config.DateColumn("Дата", format="DD.MM.YYYY"),
            "Время": st.column_config.TimeColumn("Время"),
            "Pre-market": st.column_config.TextColumn("Pre-market", max_chars=80),
            "Plan": st.column_config.TextColumn("Plan", max_chars=80),
            "Post": st.column_config.TextColumn("Post", max_chars=80),
        },
    )

    table_state = st.session_state.get(table_key, {})
    selected_rows = table_state.get("selection", {}).get("rows") if table_state else None
    selection_key = f"{table_key}_selection"
    current_selection = tuple(selected_rows) if selected_rows else ()
    previous_selection = st.session_state.get(selection_key)
    if previous_selection == current_selection:
        return False, None
    st.session_state[selection_key] = current_selection

    if not current_selection:
        return True, None

    selected_idx = current_selection[-1]
    return True, int(df.iloc[selected_idx]["id"])
