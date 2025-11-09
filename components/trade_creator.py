"""Упрощённая форма создания сделки (trade_creator)."""

from typing import Any, Dict, Optional

import streamlit as st

from .trade_manager.constants import CREATE_ALLOWED_STATUSES
from .trade_manager.defaults import build_trade_defaults
from .trade_manager.sections import render_open_stage
from db import create_trade, list_accounts, list_analysis, list_setups
from helpers import option_with_placeholder


def render_trade_creator(*, context: str = "default") -> Optional[int]:
    """Показывает форму создания сделки и возвращает ID новой записи."""

    trade_key = f"creator_{context}"

    accounts = option_with_placeholder(
        list_accounts(),
        placeholder="— Account not selected —",
        formatter=lambda acc: f"{acc['name']} (#{acc['id']})",
    )
    setups = option_with_placeholder(
        list_setups(),
        placeholder="— Setup not selected —",
        formatter=lambda setup: f"{setup['name']} (#{setup['id']})",
    )
    analyses = option_with_placeholder(
        list_analysis(),
        placeholder="— Analysis not linked —",
        formatter=lambda analysis: f"{analysis.get('date_local') or 'No date'} · {analysis.get('asset') or '—'} (#{analysis['id']})",
    )

    account_labels = list(accounts.keys())
    setup_labels = list(setups.keys())
    analysis_labels = list(analyses.keys())

    defaults = build_trade_defaults({}, accounts, analyses, setups)
    open_defaults = defaults["open"]

    status_container = st.container(border=True)
    with status_container:
        selected_state = st.selectbox(
            "Trade status",
            CREATE_ALLOWED_STATUSES,
            index=0,
            key=f"tc_status_{trade_key}",
            help="Доступные статусы при создании сделки.",
        )

    open_values = render_open_stage(
        trade_key=trade_key,
        visible=True,
        expanded=True,
        defaults=open_defaults,
        account_labels=account_labels,
        assets=open_defaults["asset_options"],
        analysis_labels=analysis_labels,
        setup_labels=setup_labels,
    )

    submitted = st.button(
        "Create",
        type="primary",
        use_container_width=True,
        key=f"tc_submit_{trade_key}",
    )
    if not submitted:
        return None

    payload: Dict[str, Any] = {
        "date_local": open_values["date"].isoformat(),
        "time_local": open_values["time"].strftime("%H:%M:%S"),
        "account_id": accounts[open_values["account_label"]],
        "asset": open_values["asset"],
        "analysis_id": analyses[open_values["analysis_label"]],
        "setup_id": setups[open_values["setup_label"]],
        "risk_pct": float(open_values["risk_pct"]),
        "state": selected_state,
    }

    try:
        new_trade_id = create_trade(payload)
        st.success("Сделка создана.")
        return new_trade_id
    except Exception as exc:  # pragma: no cover - UI feedback
        st.error(f"Failed to create the trade: {exc}")
        return None
