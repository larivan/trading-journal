"""Основной компонент трейд-менеджера."""

from typing import Any, Dict, List
import streamlit as st
from components.chart_editor import persist_chart_editor, render_chart_editor
from helpers import to_option_format, parse_date, parse_time
from utils.trade_sessions import detect_trade_session
from utils.session_state import dialog_is_active, close_dialog
from config import LOCAL_TZ
from .state import get_allowed_statuses, visible_stages
from .defaults import get_trade_defaults
from .sections import (
    render_main_stage,
    render_close_stage,
    render_review_stage,
)
from db import (
    create_trade,
    delete_trade,
    get_trade_by_id,
    list_accounts,
    list_analysis,
    list_setups,
    list_trade_charts,
    attach_chart_to_trade,
    update_trade,
)


def render_trade_manager() -> None:
    """Единое окно создания и редактирования сделок."""
    trade_id = None
    is_new_trade = True
    if "tm_trade_id" in st.session_state:
        is_new_trade = False
        trade_id = st.session_state["tm_trade_id"]

    if "tm_success_message" in st.session_state:
        st.toast(st.session_state.pop("tm_success_message"), icon="🔥")

    trade: Dict[str, Any] = {}

    if not is_new_trade:
        trade = get_trade_by_id(trade_id)
        if not trade:
            st.error("Trade not found.")
            st.session_state.pop("tm_trade_id", None)
            close_dialog()
            st.rerun()
            return

    @st.dialog(_get_dialog_title(trade, is_new_trade), width="large", on_dismiss=_handle_dialog_dismiss)
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
        defaults = get_trade_defaults(
            trade,
            accounts,
            analyses,
            setups
        )
        charts = list_trade_charts(trade_id)

        # Рендерим хедер с выбором статуса и кнопками действий
        with st.container(border=True):
            status_col, message_col, actions_col = st.columns(
                [0.2, 0.6, 0.2],
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
                submitted = actions_col.button(
                    "Save",
                    type="primary",
                    width="stretch"
                )

        stages_col, side_col = st.columns([1, 2])

        # Рендерим стадии сделки
        with stages_col:
            visible = visible_stages(selected_status)

            main_values = render_main_stage(
                expanded=(selected_status in ("Open", "Cancel", "Miss")),
                defaults=defaults["open"],
                account_options=accounts,
                analysis_options=analyses,
                setup_options=setups,
            )

            close_values = render_close_stage(
                visible="close" in visible,
                expanded=("Close" == selected_status),
                defaults=defaults['close'],
            )

            review_values = render_review_stage(
                visible="review" in visible,
                expanded=("Review" == selected_status),
                defaults=defaults['review'],
            )

        # Панель с редактором графиков
        with side_col:
            current_charts = render_chart_editor(
                key=f"tm_chart_editor_new_trade",
                base_rows=charts,
                layout_columns=2,
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

        if is_new_trade:
            payload["local_tz"] = local_tz

            try:
                new_trade_id = create_trade(payload)
            except Exception as exc:
                message_col.error(f"Failed to create the trade: {exc}")
                return

            try:
                persist_chart_editor(
                    attached_charts=[],
                    editor_rows=current_charts,
                    attach_chart=lambda chart_id, trade_id=new_trade_id: attach_chart_to_trade(  # noqa: E731
                        trade_id, chart_id
                    ),
                )
            except Exception as exc:
                message_col.error(
                    f"Trade rolled back because charts could not be saved: {exc}"
                )
                return

            st.session_state["tm_trade_id"] = new_trade_id
            st.session_state["tm_success_message"] = "Trade created."
        else:
            try:
                update_trade(trade_id, payload)
            except Exception as exc:
                message_col.error(f"Failed to persist the trade: {exc}")
                return

            try:
                persist_chart_editor(
                    attached_charts=charts,
                    editor_rows=current_charts,
                    attach_chart=lambda chart_id, trade_id=trade_id: attach_chart_to_trade(  # noqa: E731
                        trade_id, chart_id
                    ),
                )
            except Exception as exc:  # pragma: no cover - UI feedback
                message_col.error(
                    f"Trade saved but failed to update charts: {exc}"
                )
                return

            st.session_state["tm_success_message"] = "Trade saved."
        st.rerun()

    if dialog_is_active("trade_manager"):
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
    close_dialog()
    st.session_state.pop("tm_trade_id", None)
