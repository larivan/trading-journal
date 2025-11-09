"""Основной компонент трейд-менеджера."""

from typing import Any, Dict, List, Optional

import streamlit as st

from db import (
    list_accounts,
    list_analysis,
    list_setups,
    parse_emotional_problems,
    update_trade,
)
from helpers import option_with_placeholder

from .constants import RESULT_PLACEHOLDER, STATUS_STAGE
from .defaults import build_trade_defaults
from .sections import (
    render_closed_stage,
    render_header_actions,
    render_open_stage,
    render_review_stage,
)
from .state import allowed_statuses, visible_stages
from .view import render_view_tab


def render_trade_manager(trade: Dict[str, Any]) -> None:
    """Главный UI-компонент трейд-менеджера для существующих сделок."""

    if not trade or trade.get("id") is None:
        raise ValueError("render_trade_manager требует существующую сделку")

    trade_id = trade["id"]
    trade_key = str(trade_id)

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

    defaults = build_trade_defaults(trade, accounts, analyses, setups)
    open_defaults = defaults["open"]
    closed_defaults = defaults["closed"].copy()
    review_defaults = defaults["review"].copy()

    emotional_defaults = parse_emotional_problems(
        closed_defaults.pop("emotional"))

    current_state = trade.get("state") or "open"
    tab_labels: List[str] = ["Options", "View"]

    tabs = st.tabs(tab_labels)
    tab_map = {label: tab for label, tab in zip(tab_labels, tabs)}

    selected_state = current_state
    closed_inputs: Dict[str, Any] = {}
    review_inputs: Optional[Dict[str, Any]] = None
    open_values = open_defaults.copy()
    submitted = False

    with tab_map["Options"]:
        header_container = st.container(border=True)
        with header_container:
            status_col, _, actions_col = st.columns(
                [0.2, 0.3, 0.5],
                gap="large",
                vertical_alignment="bottom",
            )
            with status_col:
                allowed = allowed_statuses(current_state)
                current_state = current_state if current_state in allowed else allowed[0]
                selected_state = st.selectbox(
                    "Trade status",
                    allowed,
                    index=allowed.index(current_state),
                    help="Statuses move sequentially similar to Jira.",
                    key=f"tm_status_{trade_key}",
                )
            with actions_col:
                submitted = render_header_actions(trade_key)

        stages = visible_stages(selected_state)
        expanded_stage = STATUS_STAGE.get(selected_state, stages[0])
        if expanded_stage not in stages:
            expanded_stage = stages[0]

        open_values = render_open_stage(
            trade_key=trade_key,
            visible="open" in stages,
            expanded=(expanded_stage == "open"),
            defaults=open_defaults,
            account_labels=account_labels,
            assets=open_defaults["asset_options"],
            analysis_labels=analysis_labels,
            setup_labels=setup_labels,
        )

        closed_inputs, emotional_defaults = render_closed_stage(
            trade_key=trade_key,
            visible="closed" in stages,
            expanded=(expanded_stage == "closed"),
            defaults=closed_defaults,
            emotional_defaults=emotional_defaults,
        )

        review_inputs = render_review_stage(
            trade_key=trade_key,
            visible="review" in stages,
            expanded=(expanded_stage == "review"),
            defaults=review_defaults,
        )

    with tab_map["View"]:
        render_view_tab(
            trade,
            account_label=open_values["account_label"],
            setup_label=open_values["setup_label"],
            analysis_label=open_values["analysis_label"],
        )

    if not submitted:
        return

    errors: List[str] = []
    if selected_state in ("closed", "reviewed"):
        if not closed_inputs:
            errors.append("Fill in the “After close” block.")
        else:
            if closed_inputs["result"] == RESULT_PLACEHOLDER:
                errors.append("Select the trade result.")
            if closed_inputs["net_pnl"] is None:
                errors.append("Provide Net PnL.")
    if errors:
        for err in errors:
            st.error(err)
        return

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

    if closed_inputs:
        payload.update({
            "result": None if closed_inputs["result"] == RESULT_PLACEHOLDER else closed_inputs["result"],
            "net_pnl": float(closed_inputs["net_pnl"]),
            "risk_reward": float(closed_inputs["risk_reward"]),
            "reward_percent": float(closed_inputs["reward_percent"]),
            "hot_thoughts": closed_inputs["hot_thoughts"].strip() or None,
            "emotional_problems": emotional_defaults or None,
        })
    else:
        payload.update({
            "result": None,
            "net_pnl": None,
            "risk_reward": None,
            "reward_percent": None,
            "hot_thoughts": None,
            "emotional_problems": None,
        })

    if review_inputs:
        estimation_value = review_inputs["estimation"]
        payload.update({
            "cold_thoughts": review_inputs["cold_thoughts"].strip() or None,
            "estimation": estimation_value if estimation_value in (0, 1) else None,
        })
    else:
        existing_estimation = trade.get("estimation")
        payload.update({
            "cold_thoughts": None if selected_state != "reviewed" else trade.get("cold_thoughts"),
            "estimation": existing_estimation if selected_state == "reviewed" and existing_estimation in (0, 1) else None,
        })

    try:
        update_trade(trade_id, payload)
        st.success("Trade updated.")
        st.rerun()
    except Exception as exc:  # pragma: no cover - UI feedback
        st.error(f"Failed to persist the trade: {exc}")
