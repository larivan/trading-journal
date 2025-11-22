"""Основной компонент трейд-менеджера."""

from typing import Any, Callable, Dict, List, Optional

import streamlit as st

from db import (
    add_note,
    attach_chart_to_trade,
    attach_note_to_trade,
    create_trade,
    detach_note_from_trade,
    get_trade_by_id,
    list_accounts,
    list_analysis,
    list_notes,
    list_setups,
    list_trade_charts,
    list_trade_notes,
    parse_emotional_problems,
    update_trade,
)
from components.chart_editor import (
    chart_editor_value_state_key,
    chart_table_rows,
    normalize_editor_rows,
    persist_chart_editor,
    render_chart_editor,
)
from components.note_editor import render_note_editor
from components.state_header import render_entity_header
from helpers import option_with_placeholder, parse_trade_date, parse_trade_time
from utils.trade_sessions import detect_trade_session

from config import LOCAL_TZ
from .defaults import build_trade_defaults
from .sections import (
    render_closed_stage,
    render_open_stage,
    render_review_stage,
)
from .state import allowed_statuses, visible_stages
from .constants import (
    STATUS_STAGE,
    RESULT_PLACEHOLDER,
    CREATE_ALLOWED_STATUSES
)


def render_trade_manager(
    *,
    trade_id: Optional[int] = None,
    on_created: Optional[Callable[[int], None]] = None,
    on_close: Optional[Callable[[], None]] = None,
) -> None:
    """Единое окно создания и редактирования сделок."""

    is_new_trade = trade_id is None
    trade: Dict[str, Any] = {}
    trade_error: Optional[str] = None
    trade_error_level: Optional[str] = None
    if not is_new_trade:
        if not trade_id:
            trade_error = "Сделка не выбрана."
            trade_error_level = "info"
        else:
            existing = get_trade_by_id(trade_id)
            if not existing:
                trade_error = "Сделка не найдена."
                trade_error_level = "error"
            else:
                trade = existing

    def _format_trade_title(data: Dict[str, Any]) -> str:
        asset_value = (data.get("asset") or "Trade").strip() or "Trade"
        date_value = parse_trade_date(data.get("date_local"))
        time_value = parse_trade_time(data.get("time_local"))
        date_label = date_value.strftime("%d.%m.%Y") if date_value else "—"
        time_label = time_value.strftime("%H:%M") if time_value else "—"
        return f"{asset_value} · {date_label} - {time_label}"

    dialog_title = "New trade"
    if not is_new_trade:
        dialog_title = (
            "Trade"
            if trade_error
            else _format_trade_title(trade)
        )

    @st.dialog(dialog_title, width="large")
    def _dialog() -> None:
        if trade_error:
            status_fn = st.info if trade_error_level == "info" else st.error
            status_fn(trade_error)
            return

        trade_key = "create" if is_new_trade else f"edit_{trade_id}"

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

        current_state = trade.get("state") or CREATE_ALLOWED_STATUSES[0]
        selected_state = current_state
        closed_inputs: Dict[str, Any] = {}
        review_inputs: Optional[Dict[str, Any]] = None
        open_values = open_defaults.copy()
        submitted = False
        trade_charts = list_trade_charts(trade_id) if not is_new_trade else []
        chart_rows_source = chart_table_rows(trade_charts)
        trade_notes = list_trade_notes(trade_id) if not is_new_trade else []
        all_notes = list_notes()

        chart_editor_value: Optional[Any] = None
        pending_notes_key = f"tm_pending_notes_{trade_key}"

        def _coerce_note_id(value: Any) -> Optional[int]:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        def _pending_note_ids() -> List[int]:
            raw = st.session_state.get(pending_notes_key, [])
            if not isinstance(raw, list):
                st.session_state[pending_notes_key] = []
                return []
            cleaned: List[int] = []
            for value in raw:
                note_id = _coerce_note_id(value)
                if note_id is None or note_id in cleaned:
                    continue
                cleaned.append(note_id)
            st.session_state[pending_notes_key] = cleaned
            return cleaned

        def _reset_creation_buffers() -> None:
            if not is_new_trade:
                return
            st.session_state.pop(pending_notes_key, None)
            chart_state_key = chart_editor_value_state_key(
                f"tm_chart_editor_{trade_key}"
            )
            st.session_state.pop(chart_state_key, None)

        header_container = st.container(border=True)
        with header_container:
            allowed = (
                CREATE_ALLOWED_STATUSES
                if is_new_trade
                else allowed_statuses(current_state)
            )
            current_state = current_state if current_state in allowed else allowed[0]

            def _submit_action() -> None:
                st.session_state[f"tm_submit_triggered_{trade_key}"] = True

            def _cancel_action() -> None:
                if is_new_trade:
                    _reset_creation_buffers()
                if on_close:
                    on_close()

            selected_state = render_entity_header(
                status_label="Trade status",
                status_options=allowed,
                current_status=current_state,
                status_key=f"tm_status_{trade_key}",
                actions=[
                    {
                        "label": "Save",
                        "type": "primary",
                        "key": f"tm_submit_{trade_key}",
                        "on_click": _submit_action,
                    },
                    {
                        "label": "Cancel",
                        "key": f"tm_cancel_{trade_key}",
                        "on_click": _cancel_action,
                        "type": "secondary",
                        "disabled": on_close is None,
                    },
                ],
            )
            submitted = st.session_state.pop(
                f"tm_submit_triggered_{trade_key}", False)

        stages_col, side_col = st.columns([1, 2])

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
            chart_editor_value = render_chart_editor(
                key=f"tm_chart_editor_{trade_key}",
                base_rows=chart_rows_source,
                layout_columns=2,
            )
            st.divider()
            note_attach_fn: Callable[[int], None]
            note_detach_fn: Callable[[int], None]
            attached_notes: List[Dict[str, Any]]
            if is_new_trade:
                pending_ids = _pending_note_ids()

                def _attach_pending(note_id: int) -> None:
                    clean_id = _coerce_note_id(note_id)
                    if clean_id is None:
                        return
                    ids = _pending_note_ids()
                    if clean_id not in ids:
                        ids.append(clean_id)
                        st.session_state[pending_notes_key] = ids

                def _detach_pending(note_id: int) -> None:
                    clean_id = _coerce_note_id(note_id)
                    if clean_id is None:
                        return
                    ids = [nid for nid in _pending_note_ids()
                           if nid != clean_id]
                    st.session_state[pending_notes_key] = ids

                note_attach_fn = _attach_pending
                note_detach_fn = _detach_pending
                note_index = {note["id"]: note for note in all_notes}
                attached_notes = [
                    note_index[note_id]
                    for note_id in pending_ids
                    if note_id in note_index
                ]
            else:
                def note_attach_fn(note_id, t_id=trade_id): return attach_note_to_trade(  # noqa: E731
                    t_id, note_id
                )

                def note_detach_fn(note_id, t_id=trade_id): return detach_note_from_trade(  # noqa: E731
                    t_id, note_id
                )
                attached_notes = trade_notes

            render_note_editor(
                key=f"trade_{trade_key}",
                attached_notes=attached_notes,
                attach_note=note_attach_fn,
                detach_note=note_detach_fn,
                create_note=lambda title, body: add_note(title, body),
                all_notes=all_notes,
                title="Notes",
                selection_label="Linked notes",
                popover_label="Add",
                create_button_label="Create note",
                empty_warning="Note body cannot be empty.",
                success_update_message="Notes updated.",
                success_create_message="Note created and attached.",
                error_update_message="Failed to update notes: {exc}",
                error_create_message="Failed to add note: {exc}",
                column_ratio=(0.6, 0.4),
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

        trade_local_tz = trade.get("local_tz") or LOCAL_TZ
        session_value = detect_trade_session(
            open_values["date"],
            open_values["time"],
            local_tz_label=trade_local_tz,
        )

        payload: Dict[str, Any] = {
            "date_local": open_values["date"].isoformat(),
            "time_local": open_values["time"].strftime("%H:%M:%S"),
            "account_id": accounts[open_values["account_label"]],
            "asset": open_values["asset"],
            "analysis_id": analyses[open_values["analysis_label"]],
            "setup_id": setups[open_values["setup_label"]],
            "risk_pct": float(open_values["risk_pct"]),
            "state": selected_state,
            "session": session_value,
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

        chart_state_payload = chart_editor_value if chart_editor_value is not None else chart_rows_source
        chart_editor_rows = normalize_editor_rows(chart_state_payload)

        if is_new_trade:
            payload["local_tz"] = trade_local_tz
            try:
                new_trade_id = create_trade(payload)
                persist_chart_editor(
                    attached_charts=[],
                    editor_rows=chart_editor_rows,
                    attach_chart=lambda chart_id, trade_id=new_trade_id: attach_chart_to_trade(  # noqa: E731
                        trade_id, chart_id
                    ),
                )
                for note_id in _pending_note_ids():
                    attach_note_to_trade(new_trade_id, note_id)
                _reset_creation_buffers()
                # st.success("Сделка создана.")
                if on_created:
                    on_created(new_trade_id)
                else:
                    st.rerun()
            except Exception as exc:  # pragma: no cover - UI feedback
                st.error(f"Failed to create the trade: {exc}")
        else:
            try:
                persist_chart_editor(
                    attached_charts=trade_charts,
                    editor_rows=chart_editor_rows,
                    attach_chart=lambda chart_id, trade_id=trade_id: attach_chart_to_trade(  # noqa: E731
                        trade_id, chart_id
                    ),
                )
                update_trade(trade_id, payload)
                # st.success("Trade updated.")
                st.rerun()
            except Exception as exc:  # pragma: no cover - UI feedback
                st.error(f"Failed to persist the trade: {exc}")

    _dialog()
