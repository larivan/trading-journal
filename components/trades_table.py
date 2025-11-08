from typing import Optional, Tuple

import pandas as pd
import streamlit as st


def render_trades_table(
    rows,
    tab_key: str,
) -> Tuple[bool, Optional[int]]:
    """Отображает таблицу сделок и возвращает информацию о новом выборе строки."""
    if not rows:
        st.info("Нет сделок для выбранного периода.")
        return False, None

    # Приводим данные к человекочитаемому виду (русские заголовки, форматы дат/времени)
    df = pd.DataFrame(rows)
    display_columns = [
        "date_local",
        "asset",
        "state",
        "result",
        "net_pnl",
        "risk_reward",
        "session",
    ]
    table = df[display_columns].rename(columns={
        "date_local": "Дата",
        "asset": "Инструмент",
        "state": "Состояние",
        "result": "Результат",
        "net_pnl": "PnL",
        "risk_reward": "R:R",
        "session": "Сессия",
    })
    table["Дата"] = pd.to_datetime(table["Дата"], errors="coerce")
    if "time_local" in df.columns:
        table.insert(
            1,
            "Время",
            pd.to_datetime(df["time_local"], errors="coerce").dt.time,
        )
    table["Открыть"] = df["id"].apply(
        lambda tid: f"/trade-detail?trade_id={tid}"
    )

    # Храним отдельный ключ таблицы для каждого периода, чтобы isolировать выбор
    table_key = f"trades_table_{tab_key}"
    st.dataframe(
        table,
        key=table_key,
        hide_index=True,
        on_select="rerun",
        selection_mode=["single-row"],
        column_config={
            "Дата": st.column_config.DateColumn("Дата", format="DD.MM.YYYY"),
            "Время": st.column_config.TimeColumn("Время"),
            "PnL": st.column_config.NumberColumn("PnL", format="%.2f"),
            "R:R": st.column_config.NumberColumn("R:R", format="%.2f"),
            "Открыть": st.column_config.LinkColumn(
                "Открыть",
                help="Перейти на отдельную страницу сделки",
                display_text="Страница",
            ),
        },
    )

    # Анализируем state, чтобы понять изменилась ли выделенная строка
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
