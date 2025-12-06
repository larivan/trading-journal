"""Основной компонент трейд-менеджера."""

from typing import Any, Dict, List
import streamlit as st
from components.note_manager import render_note_manager
from components.chart_editor import persist_chart_editor, render_chart_editor
from components.note_selector import render_note_selector, clear_note_selector_state
from helpers import to_option_format, parse_date, parse_time
from utils.trade_sessions import detect_trade_session
from .state import get_allowed_statuses, map_status_to_outcome, visible_stages
from .defaults import get_trade_defaults
from .sections import (
    render_main_stage,
    render_close_stage,
    render_review_stage,
)
from utils.session_state import (
    open_dialog,
    close_dialog,
    dialog_is_active,
    get_previous_dialog,
    remove_previous_dialog
)
from config import (
    TRADE_DIALOG_NAME,
    TRADE_ID_STATE,
    TRADE_SUCCESS_STATE,
    TM_KEY_PREFIX,
    LOCAL_TZ,
    ANALYSIS_DIALOG_NAME
)
from db import (
    create_trade,
    delete_trade,
    get_trade_by_id,
    list_accounts,
    list_analysis,
    list_trade_notes,
    list_setups,
    list_charts,
    attach_chart_to_trade,
    attach_note_to_trade,
    detach_note_from_trade,
    update_trade,
    transaction,
)


def render_trade_manager() -> None:
    """Единое окно создания и редактирования сделок."""

    if not dialog_is_active(TRADE_DIALOG_NAME):
        render_note_manager()
        return

    trade_id = None
    is_new_trade = True
    if TRADE_ID_STATE in st.session_state:
        is_new_trade = False
        trade_id = st.session_state[TRADE_ID_STATE]

    if TRADE_SUCCESS_STATE in st.session_state:
        st.toast(st.session_state.pop(TRADE_SUCCESS_STATE), icon="🔥")

    state_key = f"{TM_KEY_PREFIX}{trade_id or 'new'}"

    trade: Dict[str, Any] = {}
    if not is_new_trade:
        trade = get_trade_by_id(trade_id)
        if not trade:
            st.error("Trade not found.")
            st.session_state.pop(TRADE_ID_STATE, None)
            close_dialog()
            st.rerun()
            return

    @st.dialog(
        _get_dialog_title(trade, is_new_trade),
        width="large",
        on_dismiss=_handle_dialog_dismiss
    )
    def _dialog() -> None:
        # Подготовка данных
        accounts = to_option_format(
            list_accounts(),
            formatter=lambda acc: f"{acc['name']}",
        )
        setups = to_option_format(
            list_setups(),
            formatter=lambda setup: f"{setup['name']}",
        )
        analyses = to_option_format(
            list_analysis(),
            formatter=lambda analysis: f"{analysis.get('date_local')} · {analysis.get('asset')}",
        )
        defaults = get_trade_defaults(trade)
        charts = list_charts(trade_id=trade_id) if trade_id else []
        base_trade_notes = list_trade_notes(trade_id) if trade_id else []

        # Рендерим хедер с выбором статуса и кнопками действий
        with st.container(border=True):
            status_col, message_col, actions_col = st.columns(
                [0.2, 0.5, 0.3],
                gap="large",
                vertical_alignment="bottom",
            )
            with status_col:
                current_status = trade.get("state")
                allowed_statuses = get_allowed_statuses(current_status)
                selected_status = st.selectbox(
                    "Trade status",
                    allowed_statuses,
                    index=allowed_statuses.index(
                        current_status) if current_status else 0
                )

            with actions_col:
                c1, c2 = st.columns(2)
                if get_previous_dialog():
                    if c1.button(
                        ":material/arrow_back: Back",
                        width="stretch"
                    ):
                        _handle_dialog_dismiss()
                        remove_previous_dialog()
                        open_dialog(get_previous_dialog())
                        st.rerun()

                submitted = c2.button(
                    "Save",
                    type="primary",
                    width="stretch"
                )

        stages_col, side_col = st.columns([1, 2])

        selected_outcome = map_status_to_outcome(
            selected_status, trade.get("outcome"))

        # Рендерим стадии сделки
        with stages_col:
            visible = visible_stages(selected_status)
            close_visible = ("close" in visible) and not (
                selected_status == "Review"
                and selected_outcome in ("canceled", "missed")
            )

            main_values = render_main_stage(
                expanded=(selected_status in ("Open", "Cancel", "Miss")),
                defaults=defaults["open"],
                account_options=accounts,
                analysis_options=analyses,
                setup_options=setups,
                state_key=f"{state_key}_main"
            )

            close_values = render_close_stage(
                visible=close_visible,
                expanded=("Close" == selected_status),
                defaults=defaults['close'],
                state_key=f"{state_key}_close"
            )

            review_values = render_review_stage(
                visible="review" in visible,
                expanded=("Review" == selected_status),
                defaults=defaults['review'],
                state_key=f"{state_key}_review"
            )

        # Панель с редактором графиков
        with side_col:
            st.markdown("#### Charts")
            current_charts = render_chart_editor(
                key=f"{state_key}_chart_editor",
                base_rows=charts,
                layout_columns=2,
            )
            st.markdown("#### Observations")
            staged_note_ids = render_note_selector(
                entity_type="trade",
                entity_id=trade_id,
                state_key=f"{state_key}_note_selector",
                previous_dialog_name=TRADE_DIALOG_NAME,
                excerpt_limit=45,
            )

        if not submitted:
            return

        # Валидация и сохранение сделки
        if selected_status in ("Open", "Cancel", "Miss"):
            if not main_values["asset"]:
                message_col.error("Select an asset.")
                return

        if selected_status == "Close":
            if not close_values:
                message_col.error("Fill in the “After close” block.")
                return
            else:
                if not close_values["result"]:
                    message_col.error("Select the trade result.")
                    return
                if close_values["net_pnl"] is None:
                    message_col.error("Provide Net PnL.")
                    return

        local_tz = trade.get("local_tz") or LOCAL_TZ
        session_value = detect_trade_session(
            main_values["date"],
            main_values["time"],
            local_tz_label=local_tz,
        )

        payload: Dict[str, Any] = {
            "date_local": main_values["date"].isoformat(),
            "time_local": main_values["time"].strftime("%H:%M:%S"),
            "account_id": main_values["account"],
            "asset": main_values["asset"],
            "analysis_id": main_values["analysis"],
            "setup_id": main_values["setup"],
            "risk_pct": float(main_values["risk_pct"]),
            "session": session_value,
            "state": selected_status,
            "outcome": selected_outcome,
        }

        if close_values:
            payload.update({
                "result": None if not close_values["result"] else close_values["result"],
                "net_pnl": float(close_values["net_pnl"]),
                "risk_reward": float(close_values["risk_reward"]),
                "reward_percent": float(close_values["reward_percent"]),
                "hot_thoughts": close_values["hot_thoughts"].strip() or None,
            })

        if review_values:
            payload.update({
                "cold_thoughts": review_values["cold_thoughts"].strip() or None,
                "estimation": review_values["estimation"],
            })

        base_note_ids = {
            note.get("id") for note in base_trade_notes if note.get("id") is not None
        }
        staged_note_ids_set = {
            int(nid) for nid in (staged_note_ids or []) if nid is not None
        }

        try:
            with transaction() as conn:
                current_trade_id = trade_id
                trade_charts = charts or []
                if is_new_trade:
                    payload["local_tz"] = local_tz
                    current_trade_id = create_trade(payload, conn=conn)
                else:
                    update_trade(current_trade_id, payload, conn=conn)

                persist_chart_editor(
                    attached_charts=trade_charts,
                    editor_rows=current_charts,
                    conn=conn,
                    attach_chart=lambda chart_id, trade_id=current_trade_id: attach_chart_to_trade(  # noqa: E731
                        trade_id, chart_id, conn=conn
                    ),
                )
                for note_id in base_note_ids - staged_note_ids_set:
                    detach_note_from_trade(
                        current_trade_id, note_id, conn=conn)
                for note_id in staged_note_ids_set - base_note_ids:
                    attach_note_to_trade(current_trade_id, note_id, conn=conn)

            if is_new_trade:
                st.session_state[TRADE_ID_STATE] = current_trade_id
                st.session_state[TRADE_SUCCESS_STATE] = "Trade created."
            else:
                st.session_state[TRADE_SUCCESS_STATE] = "Trade saved."
        except Exception as exc:  # pragma: no cover - UI feedback
            message_col.error(f"Failed to save the trade: {exc}")
            return
        st.rerun()

    if dialog_is_active(TRADE_DIALOG_NAME):
        _dialog()


def _get_dialog_title(data: Dict[str, Any], is_new_trade: bool) -> str:
    if is_new_trade:
        return "New trade"
    if not data:
        return "-"
    asset = (data.get("asset") or "Trade").strip()
    date = parse_date(data.get("date_local")).strftime("%d.%m.%Y")
    time = parse_time(data.get("time_local")).strftime("%H:%M")
    return f"{asset} · {date} - {time}"


def _handle_dialog_dismiss() -> None:
    current_trade_id = st.session_state.get(TRADE_ID_STATE)
    close_dialog()
    st.session_state.pop(TRADE_ID_STATE, None)
    st.session_state.pop("tm_default_analysis_id", None)
    clear_note_selector_state(
        f"{TM_KEY_PREFIX}{current_trade_id or 'new'}_note_selector"
    )
