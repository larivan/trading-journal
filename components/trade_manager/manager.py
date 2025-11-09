"""Основной компонент трейд-менеджера."""

from typing import Any, Dict, List, Optional, Sequence, Set

import streamlit as st

from db import (
    add_chart,
    add_note,
    attach_chart_to_trade,
    attach_note_to_trade,
    detach_note_from_trade,
    list_accounts,
    list_analysis,
    list_notes,
    list_setups,
    list_trade_charts,
    list_trade_notes,
    parse_emotional_problems,
    update_chart,
    delete_chart,
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


def render_trade_manager(
    trade: Dict[str, Any],
    *,
    context: Optional[str] = None,
    default_tab: str = "Options",
) -> None:
    """Главный UI-компонент трейд-менеджера для существующих сделок."""

    if not trade or trade.get("id") is None:
        raise ValueError("render_trade_manager требует существующую сделку")

    trade_id = trade["id"]
    trade_key = f"{context}_{trade_id}" if context else str(trade_id)

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
    tab_labels: Sequence[str] = ("Options", "View")
    if default_tab in tab_labels:
        ordered_labels = [default_tab] + [
            label for label in tab_labels if label != default_tab
        ]
    else:
        ordered_labels = list(tab_labels)

    tabs = st.tabs(ordered_labels)
    tab_map = {label: tab for label, tab in zip(ordered_labels, tabs)}

    selected_state = current_state
    closed_inputs: Dict[str, Any] = {}
    review_inputs: Optional[Dict[str, Any]] = None
    open_values = open_defaults.copy()
    submitted = False
    trade_charts = list_trade_charts(trade_id)
    trade_notes = list_trade_notes(trade_id)
    all_notes = list_notes()

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

        stages_col, side_col = st.columns([1, 2], gap="large")

        with stages_col:
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

        with side_col:
            _render_charts_section(
                trade_id=trade_id,
                trade_key=trade_key,
                attached_charts=trade_charts,
            )
            st.divider()
            _render_notes_section(
                trade_id=trade_id,
                trade_key=trade_key,
                attached_notes=trade_notes,
                all_notes=all_notes,
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


def _render_charts_section(
    *,
    trade_id: int,
    trade_key: str,
    attached_charts: List[Dict[str, Any]],
) -> None:
    st.subheader("Charts")

    state_key = f"tm_chart_editor_state_{trade_key}"
    signature_key = f"{state_key}_signature"
    seed_signature = _chart_signature(attached_charts)
    if state_key not in st.session_state or st.session_state.get(signature_key) != seed_signature:
        st.session_state[state_key] = _charts_to_editor_rows(attached_charts)
        st.session_state[signature_key] = seed_signature

    editor_value = st.data_editor(
        st.session_state[state_key],
        key=f"{state_key}_widget",
        num_rows="dynamic",
        hide_index=True,
        column_order=["chart_url", "caption", "preview"],
        column_config={
            "chart_url": st.column_config.TextColumn(
                "Chart URL",
                required=True,
                help="Paste a direct image link.",
            ),
            "caption": st.column_config.TextColumn(
                "Caption",
                required=False,
            ),
            "preview": st.column_config.ImageColumn(
                "Preview",
                help="Preview refreshes after editing the URL.",
            ),
            "id": st.column_config.Column("ID", disabled=True, required=False, width="small"),
        },
    )
    st.session_state[state_key] = _normalize_editor_rows(editor_value)

    if st.button(
        "Save charts",
        key=f"{state_key}_save",
        use_container_width=True,
    ):
        try:
            _persist_chart_editor(
                trade_id=trade_id,
                attached_charts=attached_charts,
                editor_rows=st.session_state[state_key],
            )
            st.success("Charts updated.")
            st.rerun()
        except Exception as exc:  # pragma: no cover - UI feedback
            st.error(f"Failed to update charts: {exc}")


def _render_notes_section(
    *,
    trade_id: int,
    trade_key: str,
    attached_notes: List[Dict[str, Any]],
    all_notes: List[Dict[str, Any]],
) -> None:
    st.subheader("Notes")
    note_ids = [note["id"] for note in all_notes]
    note_index = {note["id"]: note for note in all_notes}
    for note in attached_notes:
        if note["id"] not in note_index:
            note_index[note["id"]] = note
            note_ids.append(note["id"])
    selected_default = [note["id"] for note in attached_notes]

    note_key = f"tm_note_select_{trade_key}"
    selected_note_ids = st.multiselect(
        "Linked notes",
        options=note_ids,
        default=selected_default,
        key=note_key,
        format_func=lambda note_id: _note_label(note_index.get(note_id)),
    )

    _sync_note_links(
        trade_id=trade_id,
        current_ids=set(selected_default),
        selected_ids=set(selected_note_ids),
    )

    with st.popover("Add", use_container_width=True):
        new_note_title = st.text_input(
            "Title",
            key=f"tm_note_title_{trade_key}",
        )
        new_note_body = st.text_area(
            "Body",
            height=160,
            key=f"tm_note_body_{trade_key}",
        )
        if st.button(
            "Create note",
            key=f"tm_note_create_{trade_key}",
            use_container_width=True,
        ):
            body_value = new_note_body.strip()
            if not body_value:
                st.warning("Note body cannot be empty.")
            else:
                try:
                    note_id = add_note(
                        new_note_title.strip() or None,
                        body_value,
                    )
                    attach_note_to_trade(trade_id, note_id)
                    st.success("Note created and attached.")
                    st.rerun()
                except Exception as exc:  # pragma: no cover - UI feedback
                    st.error(f"Failed to add note: {exc}")


def _chart_signature(charts: List[Dict[str, Any]]) -> List[tuple]:
    return [
        (chart.get("id"), chart.get("chart_url"), chart.get("caption"))
        for chart in charts
    ]


def _charts_to_editor_rows(charts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for chart in charts:
        rows.append({
            "id": chart.get("id"),
            "chart_url": chart.get("chart_url") or "",
            "caption": chart.get("caption") or "",
            "preview": chart.get("chart_url") or "",
        })
    if not rows:
        return [{
            "id": None,
            "chart_url": "",
            "caption": "",
            "preview": "",
        }]
    return rows


def _normalize_editor_rows(editor_value: Any) -> List[Dict[str, Any]]:
    if isinstance(editor_value, list):
        raw_rows = editor_value
    elif hasattr(editor_value, "to_dict"):
        raw_rows = editor_value.to_dict("records")  # type: ignore[call-arg]
    else:
        raw_rows = []

    normalized: List[Dict[str, Any]] = []
    for row in raw_rows:
        chart_url = (row.get("chart_url") or "").strip()
        normalized.append({
            "id": row.get("id"),
            "chart_url": chart_url,
            "caption": row.get("caption") or "",
            "preview": chart_url,
        })
    return normalized


def _persist_chart_editor(
    *,
    trade_id: int,
    attached_charts: List[Dict[str, Any]],
    editor_rows: List[Dict[str, Any]],
) -> None:
    desired_rows: List[Dict[str, Any]] = []
    for row in editor_rows:
        chart_url = (row.get("chart_url") or "").strip()
        if not chart_url:
            continue
        desired_rows.append({
            "id": row.get("id"),
            "chart_url": chart_url,
            "caption": (row.get("caption") or "").strip() or None,
        })

    current_by_id = {chart["id"]: chart for chart in attached_charts}
    desired_ids = {row["id"] for row in desired_rows if row.get("id")}

    # Removed charts
    for chart_id in set(current_by_id.keys()) - desired_ids:
        if chart_id is not None:
            delete_chart(chart_id)

    # Updated charts
    for row in desired_rows:
        chart_id = row.get("id")
        if chart_id is None or chart_id not in current_by_id:
            continue
        existing = current_by_id[chart_id]
        existing_url = (existing.get("chart_url") or "").strip()
        existing_caption = (existing.get("caption") or None)
        if row["chart_url"] != existing_url or row["caption"] != existing_caption:
            update_chart(chart_id, row["chart_url"], row["caption"])

    # New charts
    for row in desired_rows:
        if row.get("id"):
            continue
        chart_id = add_chart(row["chart_url"], row["caption"])
        attach_chart_to_trade(trade_id, chart_id)


def _note_label(note: Optional[Dict[str, Any]]) -> str:
    if not note:
        return "Unknown note"
    title = (note.get("title") or "").strip()
    if title:
        return f"{title} (#{note['id']})"
    body = (note.get("body") or "").strip()
    if len(body) > 40:
        body = body[:37].rstrip() + "..."
    return f"{body or 'Untitled'} (#{note['id']})"


def _sync_note_links(
    *,
    trade_id: int,
    current_ids: Set[int],
    selected_ids: Set[int],
) -> None:
    to_attach = selected_ids - current_ids
    to_detach = current_ids - selected_ids
    if not to_attach and not to_detach:
        return
    try:
        for note_id in to_attach:
            attach_note_to_trade(trade_id, note_id)
        for note_id in to_detach:
            detach_note_from_trade(trade_id, note_id)
        st.success("Notes updated.")
        st.rerun()
    except Exception as exc:  # pragma: no cover - UI feedback
        st.error(f"Failed to update notes: {exc}")
