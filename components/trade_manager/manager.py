"""Основной компонент трейд-менеджера."""

from typing import Any, Callable, Dict, List, Optional

import streamlit as st

from db import (
    create_trade,
    attach_chart_to_trade,
    get_trade_by_id,
    list_accounts,
    list_analysis,
    list_notes,
    list_setups,
    list_trade_charts,
    list_trade_notes,
    parse_emotional_problems,
    update_trade,
    delete_trade
)
from components.chart_editor import (
    chart_table_rows,
    normalize_editor_rows,
    persist_chart_editor,
    render_chart_editor,
)
from helpers import option_with_placeholder

from config import LOCAL_TZ
from .defaults import build_trade_defaults
from .sections import (
    render_closed_stage,
    render_header_actions,
    render_open_stage,
    render_review_stage,
)
from .sections.notes import render_notes_section
from .state import allowed_statuses, visible_stages


# --- Допустимые переходы между статусами сделки ---
STATUS_TRANSITIONS: Dict[str, List[str]] = {
    "open": ["open", "closed", "cancelled"],
    "closed": ["closed", "reviewed"],
    "reviewed": ["reviewed"],
    "cancelled": ["cancelled", "reviewed"],
    "missed": ["missed", "reviewed"],
}

# --- Карта статусов к визуальным стадиям (какие блоки формы показывать) ---
STATUS_STAGE = {
    "open": "open",
    "closed": "closed",
    "reviewed": "review",
    "cancelled": "open",
    "missed": "open",
}

# --- Значение-заглушка для селекта результата ---
RESULT_PLACEHOLDER = "— Not set —"

# --- Статусы, доступные при создании сделки ---
CREATE_ALLOWED_STATUSES = ["open", "missed"]


def render_trade_creator(
    *,
    on_created: Optional[Callable[[int], None]] = None,
    on_cancel: Optional[Callable[[], None]] = None,
) -> None:
    """Показывает модалку создания новой сделки."""

    @st.dialog("Создание сделки")
    def _dialog() -> None:
        trade_key = f"trade_creator"

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
                key=f"{trade_key}_status",
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
            key=f"{trade_key}_submit",
        )
        if not submitted:
            return None

        payload: Dict[str, Any] = {
            "date_local": open_values["date"].isoformat(),
            "time_local": open_values["time"].strftime("%H:%M:%S"),
            "local_tz": LOCAL_TZ,
            "account_id": accounts[open_values["account_label"]],
            "asset": open_values["asset"],
            "analysis_id": analyses[open_values["analysis_label"]],
            "setup_id": setups[open_values["setup_label"]],
            "risk_pct": float(open_values["risk_pct"]),
            "state": selected_state,
        }

        new_trade_id = None

        try:
            new_trade_id = create_trade(payload)
            st.success("Сделка создана.")
        except Exception as exc:  # pragma: no cover - UI feedback
            st.error(f"Failed to create the trade: {exc}")

        cancel = st.button(
            "Отмена",
            key="tc_dialog_cancel",
            use_container_width=True,
        )
        if new_trade_id and on_created:
            on_created(new_trade_id)
        if cancel and on_cancel:
            on_cancel()

    _dialog()


def render_trade_editor(
    *,
    trade_id: Optional[int],
    on_close: Optional[Callable[[], None]] = None,
) -> None:
    """Показыввает модалку для редактирования существующих сделок."""

    @st.dialog("Редактирование сделки", width="large")
    def _dialog() -> None:
        if not trade_id:
            st.info("Сделка не выбрана.")
            return
        trade = get_trade_by_id(trade_id)
        if not trade:
            st.error("Сделка не найдена.")
            return

        trade_key = f"edit_{trade_id}"

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
        selected_state = current_state
        closed_inputs: Dict[str, Any] = {}
        review_inputs: Optional[Dict[str, Any]] = None
        open_values = open_defaults.copy()
        submitted = False
        trade_charts = list_trade_charts(trade_id)
        chart_rows_source = chart_table_rows(trade_charts)
        trade_notes = list_trade_notes(trade_id)
        all_notes = list_notes()

        chart_editor_value: Optional[Any] = None

        header_container = st.container(border=True)
        with header_container:
            status_col, _, actions_col = st.columns(
                [0.2, 0.4, 0.4],
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
                    key=f"tm_status_{trade_key}",
                )
            with actions_col:
                submitted = render_header_actions(
                    trade_key,
                    on_cancel=on_close,
                )

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
            )
            st.divider()
            render_notes_section(
                trade_id=trade_id,
                trade_key=trade_key,
                attached_notes=trade_notes,
                all_notes=all_notes,
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

        chart_state_payload = chart_editor_value if chart_editor_value is not None else chart_rows_source
        chart_editor_rows = normalize_editor_rows(chart_state_payload)

        try:
            persist_chart_editor(
                attached_charts=trade_charts,
                editor_rows=chart_editor_rows,
                attach_chart=lambda chart_id, trade_id=trade_id: attach_chart_to_trade(
                    trade_id, chart_id),
            )
            update_trade(trade_id, payload)
            st.success("Trade updated.")
            st.rerun()
        except Exception as exc:  # pragma: no cover - UI feedback
            st.error(f"Failed to persist the trade: {exc}")

    _dialog()


def render_trade_remover(
    *,
    trade_id: Optional[int],
    on_deleted: Optional[Callable[[], None]] = None,
    on_cancel: Optional[Callable[[], None]] = None,
) -> None:
    """Показывает модалку удаления выбранной сделки."""

    @st.dialog("Удаление сделки")
    def _dialog() -> None:
        if not trade_id:
            st.info("Сделка не выбрана.")
            return
        st.warning(
            "Сделка будет удалена безвозвратно. Подтвердите действие.",
            icon="⚠️",
        )
        col_ok, col_cancel = st.columns(2)
        confirm = col_ok.button(
            "Удалить",
            type="primary",
            use_container_width=True,
        )
        cancel = col_cancel.button(
            "Отмена",
            use_container_width=True,
        )
        if confirm:
            try:
                delete_trade(trade_id)
                st.success("Сделка удалена.")
                if on_deleted:
                    on_deleted()
                st.rerun()
            except Exception as exc:  # pragma: no cover
                st.error(f"Не удалось удалить сделку: {exc}")
        if cancel and on_cancel:
            on_cancel()

    _dialog()
