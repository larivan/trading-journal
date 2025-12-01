"""Секция работы с трейдами в рамках этапа Execution."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import streamlit as st
from helpers import parse_date
from db import delete_trade, list_trades
from components.entity_table import render_entity_table
from utils.session_state import open_dialog, set_previous_dialog
from config import TM_DEFAULT_PREFIX


def render_execution_stage(
    *,
    analysis_id: Optional[int],
    visible: bool,
    expanded: bool,
    state_key: str,
) -> None:
    """Отрисовывает таблицу трейдов, привязанных к текущему анализу."""

    if not visible:
        return

    with st.expander("Execution", expanded=expanded):
        if not analysis_id:
            st.info("Save the analysis to create and link trades.")
            return

        if st.button(
            "Create trade",
            width=200,
            key=f"{state_key}_create_trade",
        ):
            st.session_state[f"{TM_DEFAULT_PREFIX}analysis"] = analysis_id
            set_previous_dialog('analysis_manager')
            open_dialog("trade_manager")
            st.rerun()

        trades = list_trades({"analysis_id": analysis_id})

        table_columns: List[Dict[str, Any]] = [
            {
                "field": "date_local",
                "label": "Date",
                "compute": lambda row: row.get("date_local"),
                "format": parse_date,
                "id": "date_local",
            },
            {"field": "session", "label": "Session", "id": "session"},
            {"field": "asset", "label": "Asset", "id": "asset"},
            {"field": "state", "label": "Status", "id": "state"},
            {"field": "result", "label": "Result", "id": "result"},
            {"field": "net_pnl", "label": "PnL", "id": "net_pnl"},
            {"field": "risk_reward", "label": "R:R", "id": "risk_reward"},
        ]

        def _open_trade(row: Dict[str, Any]) -> None:
            trade_id = row.get("id")
            if not trade_id:
                return
            st.session_state["tm_trade_id"] = trade_id
            open_dialog("trade_manager")

        def _delete_trades(ids: List[Any]) -> None:
            if not ids:
                return
            for trade_id in ids:
                try:
                    delete_trade(trade_id)
                except Exception as exc:
                    st.toast(
                        f"Failed to delete trade #{trade_id}: {exc}", icon="❌")
            st.rerun()

        render_entity_table(
            entity_name="trade",
            key=f"{state_key}_execution_trades",
            rows=trades,
            columns=table_columns,
            empty_message="Нет трейдов для этого анализа.",
            page_size=100,
            on_open=_open_trade,
            on_delete=_delete_trades,
        )


__all__ = ["render_execution_stage"]
