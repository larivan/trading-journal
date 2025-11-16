"""Общий компонент таблиц с выбором строки."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import pandas as pd
import streamlit as st

ColumnDefinition = Dict[str, Any]


def render_entity_table(
    *,
    rows: Sequence[Dict[str, Any]],
    tab_key: str,
    session_prefix: str,
    columns: Sequence[ColumnDefinition],
    empty_message: str,
    column_config: Optional[Dict[str, st.column_config.BaseColumn]] = None,
    id_field: str = "id",
) -> Tuple[bool, Optional[int]]:
    """Показывает универсальную таблицу и возвращает информацию о выборе."""
    if not rows:
        st.info(empty_message)
        return False, None

    df = pd.DataFrame(rows)
    table = _build_table(df, columns)

    table_key = f"{session_prefix}_table_{tab_key}"
    st.dataframe(
        table,
        key=table_key,
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode=["single-row"],
        column_config=column_config or {},
    )

    selection_key = f"{table_key}_selection"
    selection_changed, selected_idx = _detect_selection_change(table_key, selection_key)
    if not selection_changed:
        return False, None
    if selected_idx is None:
        return True, None

    selected_value = df.iloc[selected_idx].get(id_field)
    try:
        return True, int(selected_value) if selected_value is not None else None
    except (TypeError, ValueError):
        return True, selected_value  # type: ignore[return-value]


def _build_table(
    df: pd.DataFrame,
    columns: Sequence[ColumnDefinition],
) -> pd.DataFrame:
    table_data: Dict[str, pd.Series] = {}
    for column in columns:
        label = column.get("label") or column.get("field")
        if not label:
            continue
        series = _column_series(df, column)
        table_data[str(label)] = series
    return pd.DataFrame(table_data)


def _column_series(df: pd.DataFrame, column: ColumnDefinition) -> pd.Series:
    if "compute" in column and callable(column["compute"]):
        series = column["compute"](df)
    else:
        field = column.get("field")
        if field and field in df.columns:
            series = df[field]
        else:
            series = pd.Series([None] * len(df))

    col_type = column.get("type")
    if col_type == "date":
        return pd.to_datetime(series, errors="coerce")
    if col_type == "time":
        return pd.to_datetime(series, errors="coerce").dt.time
    return series


def _detect_selection_change(
    table_key: str,
    selection_key: str,
) -> Tuple[bool, Optional[int]]:
    table_state = st.session_state.get(table_key, {})
    selected_rows: Optional[List[int]] = None
    if isinstance(table_state, dict):
        selection_state = table_state.get("selection")
        if isinstance(selection_state, dict):
            selected_rows = selection_state.get("rows")

    current_selection = tuple(selected_rows or ())
    previous_selection = st.session_state.get(selection_key)
    if previous_selection == current_selection:
        return False, None

    st.session_state[selection_key] = current_selection
    if not current_selection:
        return True, None
    return True, current_selection[-1]


__all__ = ["render_entity_table"]
