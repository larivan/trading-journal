"""Основной компонент трейд-менеджера."""

from typing import Any, Dict, List, Optional
import streamlit as st
from components.note_manager import render_note_manager
from components.chart_editor import persist_chart_editor, render_chart_editor
from components.note_selector import render_note_selector, clear_note_selector_state
from helpers import to_option_format, parse_date, parse_time
from utils.trade_sessions import detect_trade_session
from .state import get_allowed_states, visible_stages
from .defaults import get_trade_defaults
from .sections import (
    render_main_stage,
    render_outcome_stage,
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
    TM_DEFAULT_PREFIX,
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
        account_rows = list_accounts(include_archived=True)
        accounts = to_option_format(
            account_rows,
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
        defaults = get_trade_defaults(trade, accounts)
        charts = list_charts(trade_id=trade_id) if trade_id else []
        base_trade_notes = list_trade_notes(trade_id) if trade_id else []

        # Рендерим хедер с выбором состояния и кнопками действий
        with st.container(border=True):
            state_col, message_col, actions_col = st.columns(
                [0.2, 0.5, 0.3],
                gap="large",
                vertical_alignment="bottom",
            )
            with state_col:
                current_state = trade.get("state")
                allowed_states = get_allowed_states(current_state)
                selected_state = st.selectbox(
                    "Trade state",
                    allowed_states,
                    index=allowed_states.index(
                        current_state) if current_state else 0
                )

            with actions_col:
                c1, c2 = st.columns(2)
                if get_previous_dialog():
                    if c1.button(
                        ":material/arrow_back: Back",
                        width="stretch"
                    ):
                        prev = get_previous_dialog()
                        _handle_dialog_dismiss()
                        remove_previous_dialog()
                        open_dialog(prev)
                        st.rerun()

                submitted = c2.button(
                    "Save",
                    type="primary",
                    width="stretch"
                )

        stages_col, side_col = st.columns([1, 2])

        # Рендерим стадии сделки
        with stages_col:
            visible = visible_stages(selected_state)
            outcome_visible = "outcome" in visible

            main_values = render_main_stage(
                expanded=(selected_state == "Open"),
                defaults=defaults["open"],
                account_options=accounts,
                analysis_options=analyses,
                setup_options=setups,
                state_key=f"{state_key}_main",
                on_risk_change=_calculate_rewards,
            )

            outcome_values = render_outcome_stage(
                visible=outcome_visible,
                expanded=(selected_state == "Outcome"),
                defaults=defaults['outcome'],
                state_key=f"{state_key}_outcome",
                is_missed=main_values["is_missed"],
                on_change=_calculate_rewards,
            )

            review_values = render_review_stage(
                visible="review" in visible,
                expanded=(selected_state == "Reviewed"),
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
                excerpt_limit=120,
            )

        if not submitted:
            return

        # Валидация и сохранение сделки
        if not main_values["asset"]:
            message_col.error("Select an asset.")
            return
        if not main_values["account"]:
            message_col.error("Select an account.")
            return

        if selected_state in ("Outcome"):
            if not outcome_values:
                message_col.error("Fill in the “Outcome” block.")
                return
            if outcome_values["net_pnl"] is None:
                message_col.error("Provide Net PnL.")
                return
        if selected_state in ("Reviewed"):
            if review_values["estimation"] is None:
                message_col.error("Provide trade estimation.")
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
            "state": selected_state,
            "is_missed": int(main_values["is_missed"]),
        }

        if outcome_values:
            payload.update({
                "net_pnl": outcome_values["net_pnl"],
                "risk_reward": outcome_values["risk_reward"],
                "reward_percent": outcome_values["reward_percent"],
                "hot_thoughts": outcome_values["hot_thoughts"].strip() or None,
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
            with st.spinner("Saving..."):
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
    st.session_state.pop(f"{TM_DEFAULT_PREFIX}analysis", None)
    clear_note_selector_state(
        f"{TM_KEY_PREFIX}{current_trade_id or 'new'}_note_selector"
    )


def _get_account_id_by_label(label: str) -> Optional[int]:
    """Возвращает ID счёта по его названию."""
    account_rows = list_accounts(include_archived=True)
    for acc in account_rows:
        if acc.get("name") == label:
            return acc.get("id")
    return None


def _calculate_rewards() -> None:
    """Высчитывает R:R и Reward % исходя из Net PnL, размера счёта и процента риска."""
    trade_id = None
    if TRADE_ID_STATE in st.session_state:
        trade_id = st.session_state[TRADE_ID_STATE]
    state_key = f"{TM_KEY_PREFIX}{trade_id or 'new'}"

    widget_keys = {
        "risk_pct": f"{state_key}_main_risk_pct",
        "is_missed": f"{state_key}_main_is_missed",
        "net_pnl": f"{state_key}_outcome_net_pnl",
        "risk_reward": f"{state_key}_outcome_risk_reward",
        "reward_percent": f"{state_key}_outcome_reward_percent",
    }

    risk_pct = st.session_state.get(widget_keys["risk_pct"])
    is_missed = st.session_state.get(widget_keys["is_missed"])
    net_pnl = st.session_state.get(widget_keys["net_pnl"])
    risk_reward = st.session_state.get(widget_keys["risk_reward"])
    account = st.session_state.get(f"{state_key}_main_account")
    if not account:
        return
    account_id = _get_account_id_by_label(account["label"])
    account_balance = _get_account_balance(account_id)
    if not account_balance or not risk_pct:
        return
    if is_missed:
        if risk_reward is None:
            return
        st.session_state[widget_keys["net_pnl"]] = float(0)
        st.session_state[widget_keys["reward_percent"]
                         ] = round(risk_pct * risk_reward, 2)
    else:
        if net_pnl is None:
            return
        st.session_state[widget_keys["risk_reward"]
                         ] = round(net_pnl / (account_balance * (risk_pct / 100)), 2)
        st.session_state[widget_keys["reward_percent"]] = round((
            net_pnl / account_balance) * 100, 2)


def _get_account_balance(account_id: Optional[int]) -> Optional[float]:
    """Возвращает стартовый баланс счёта по его ID."""
    accounts = list_accounts(include_archived=True)
    if account_id is None:
        return None
    for acc in accounts:
        if acc.get("id") == account_id:
            starting_balance = acc.get("starting_balance")
            try:
                return float(starting_balance) if starting_balance is not None else None
            except (TypeError, ValueError):
                return None
    return None
