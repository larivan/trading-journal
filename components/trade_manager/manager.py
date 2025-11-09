"""Основной компонент трейд-менеджера."""

from typing import Any, Dict, List, Optional, Set

import streamlit as st

from config import ASSETS
from db import (
    create_trade,
    list_accounts,
    list_analysis,
    list_charts_for_trade,
    list_notes_for_trade,
    list_setups,
    parse_emotional_problems,
    replace_trade_charts,
    replace_trade_notes,
    update_trade,
)
from helpers import (
    current_option_label,
    option_with_placeholder,
    parse_trade_date,
    parse_trade_time,
)

from .constants import CREATE_ALLOWED_STATUSES, RESULT_PLACEHOLDER
from .notes import (
    build_charts_dataframe,
    build_notes_dataframe,
    prepare_chart_records,
    prepare_note_records,
)
from .sections import (
    render_charts_block,
    render_closed_stage,
    render_header_actions,
    render_notes_block,
    render_open_stage,
    render_review_stage,
)
from .state import allowed_statuses, visible_stages
from .view import render_view_tab


def _trade_defaults(trade: Dict[str, Any], accounts, analyses, setups) -> Dict[str, Any]:
    """Собирает исходные значения для всех блоков Options-вкладки."""
    date_value = parse_trade_date(trade.get("date_local"))
    time_value = parse_trade_time(trade.get("time_local"))
    account_label = current_option_label(accounts, trade.get("account_id"))
    analysis_label = current_option_label(analyses, trade.get("analysis_id"))
    setup_label = current_option_label(setups, trade.get("setup_id"))
    asset_candidates = ASSETS or [trade.get("asset") or "—"]
    asset_default = trade.get("asset") if trade.get("asset") in asset_candidates else asset_candidates[0]
    if asset_default not in asset_candidates:
        asset_candidates = [asset_default] + asset_candidates
    return {
        "open": {
            "date": date_value,
            "time": time_value,
            "account_label": account_label,
            "asset": asset_default,
            "analysis_label": analysis_label,
            "setup_label": setup_label,
            "risk_pct": float(trade.get("risk_pct") or 1.0),
            "asset_options": asset_candidates,
        },
        "closed": {
            "result": trade.get("result") or RESULT_PLACEHOLDER,
            "net_pnl": trade.get("net_pnl") or 0.0,
            "risk_reward": trade.get("risk_reward") or 0.0,
            "reward_percent": trade.get("reward_percent") or 0.0,
            "hot_thoughts": trade.get("hot_thoughts") or "",
            "emotional": trade.get("emotional_problems"),
        },
        "review": {
            "cold_thoughts": trade.get("cold_thoughts") or "",
            "estimation": trade.get("estimation") or 0,
        },
    }


def render_trade_manager(
    trade: Optional[Dict[str, Any]],
    *,
    mode: str = "edit",
    context: str = "default",
    default_tab: str = "Options",
) -> None:
    """Главный UI-компонент трейд-менеджера с вкладками Options/View."""
    if mode not in {"edit", "create"}:
        raise ValueError("mode должен быть 'edit' или 'create'")

    trade = trade or {}
    trade_id = trade.get("id")
    trade_key = str(trade_id or context)
    is_create = (mode == "create") and trade_id is None

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

    defaults = _trade_defaults(trade, accounts, analyses, setups)
    open_defaults = defaults["open"]
    closed_defaults = defaults["closed"].copy()
    review_defaults = defaults["review"].copy()

    emotional_defaults = parse_emotional_problems(closed_defaults.pop("emotional"))

    if trade_id:
        trade_notes = list_notes_for_trade(trade_id)
        trade_charts = list_charts_for_trade(trade_id)
    else:
        trade_notes = []
        trade_charts = []

    observations_df = build_notes_dataframe(trade_notes)
    existing_note_ids: Set[int] = {
        int(note["id"]) for note in trade_notes if note.get("id") is not None
    }
    tag_options = sorted({tag for tags in observations_df["tags"].tolist() for tag in tags})
    charts_df = build_charts_dataframe(trade_charts)
    charts_state_key = f"tm_charts_state_{trade_key}"
    if charts_state_key not in st.session_state:
        st.session_state[charts_state_key] = charts_df.copy()
    charts_editor = st.session_state[charts_state_key]

    current_state = trade.get("state") or "open"
    if is_create and current_state not in CREATE_ALLOWED_STATUSES:
        current_state = CREATE_ALLOWED_STATUSES[0]

    if is_create:
        tab_labels: List[str] = ["Options"]
    else:
        tab_labels = ["Options", "View"]
    st.markdown(
        """
        <style>
        div[data-baseweb="tab"] button {
            font-size: 1.05rem;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    tabs = st.tabs(tab_labels)
    tab_map = {label: tab for label, tab in zip(tab_labels, tabs)}

    selected_state = current_state
    closed_inputs: Dict[str, Any] = {}
    review_inputs: Optional[Dict[str, Any]] = None
    open_values = open_defaults.copy()
    observations_editor = observations_df.copy()
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
                allowed = CREATE_ALLOWED_STATUSES if is_create else allowed_statuses(current_state)
                current_state = current_state if current_state in allowed else allowed[0]
                selected_state = st.selectbox(
                    "Trade status",
                    allowed,
                    index=allowed.index(current_state),
                    help="Statuses move sequentially similar to Jira.",
                    key=f"tm_status_{trade_key}",
                )
            with actions_col:
                submitted = render_header_actions(trade_key, is_create=is_create)

        stages = visible_stages(selected_state)
        expanded_stage = selected_state if selected_state in stages else stages[0]

        col1, col2 = st.columns([1, 2])
        with col1:
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

        with col2:
            charts_editor = render_charts_block(
                trade_key=trade_key,
                charts_editor=charts_editor,
            )
            st.session_state[charts_state_key] = charts_editor

            observations_editor = render_notes_block(
                trade_key=trade_key,
                observations_editor=observations_df,
                tag_options=tag_options,
            )

    if not is_create:
        with tab_map["View"]:
            render_view_tab(
                trade,
                trade_notes,
                trade_charts,
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
        payload.update({
            "cold_thoughts": review_inputs["cold_thoughts"].strip() or None,
            "estimation": int(review_inputs["estimation"]),
        })
    else:
        payload.update({
            "cold_thoughts": None if selected_state != "reviewed" else trade.get("cold_thoughts"),
            "estimation": None if selected_state != "reviewed" else trade.get("estimation"),
        })

    note_records = prepare_note_records(observations_editor, existing_note_ids)
    chart_records = prepare_chart_records(charts_editor)

    try:
        if is_create:
            new_trade_id = create_trade(payload)
            replace_trade_notes(new_trade_id, note_records)
            replace_trade_charts(new_trade_id, chart_records)
            st.session_state[f"tm_{context}_created_id"] = new_trade_id
            st.session_state["selected_trade_id"] = new_trade_id
            st.session_state.pop(charts_state_key, None)
            st.success("Сделка создана.")
        else:
            if trade_id is None:
                raise ValueError("Не выбран trade_id для режима редактирования")
            update_trade(trade_id, payload)
            replace_trade_notes(trade_id, note_records)
            replace_trade_charts(trade_id, chart_records)
            st.session_state.pop(charts_state_key, None)
            st.success("Trade updated.")
        st.rerun()
    except Exception as exc:  # pragma: no cover - UI feedback
        st.error(f"Failed to persist the trade: {exc}")


def reset_trade_manager_context(context: str, *, trade_id: Optional[int] = None) -> None:
    """Очищает вспомогательные ключи session_state для менеджера."""
    prefix = f"tm_{context}"
    st.session_state.pop(f"{prefix}_created_id", None)
    st.session_state.pop(f"tm_charts_state_{context}", None)
    if trade_id is not None:
        st.session_state.pop(f"tm_charts_state_{trade_id}", None)
