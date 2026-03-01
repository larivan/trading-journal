"""Страница редактирования/создания трейда."""

from typing import Any, Dict, Optional

import streamlit as st

from components.chart_editor import persist_chart_editor, render_chart_editor
from components.note_manager import render_note_manager
from components.note_selector import render_note_selector, clear_note_selector_state
from components.trade_manager.defaults import get_trade_defaults
from components.trade_manager.sections import (
    render_main_stage,
    render_outcome_stage,
    render_review_stage,
)
from components.trade_manager.state import get_allowed_states, visible_stages
from config import (
    ASSETS_VALUES,
    LOCAL_TZ,
    TM_KEY_PREFIX,
    TM_DEFAULT_PREFIX,
)
from db import (
    attach_chart_to_trade,
    attach_note_to_trade,
    create_trade,
    delete_trade,
    detach_note_from_trade,
    get_trade_by_id,
    list_charts,
    list_trade_notes,
    transaction,
    update_trade,
)
from helpers import parse_date, parse_time, to_option_format
from utils.auth import get_current_user_id, get_setting
from utils.cached_data import cached_accounts, cached_analysis, cached_setups
from utils.trade_sessions import detect_trade_session

st.set_page_config(layout="wide")

user_id = get_current_user_id()

# --- Читаем trade_id из URL-параметров ---
params = st.query_params
trade_id_str = params.get("id")
trade_id: Optional[int] = int(trade_id_str) if trade_id_str else None
is_new_trade = trade_id is None

# --- Загружаем трейд из БД ---
trade: Dict[str, Any] = {}
if not is_new_trade:
    trade = get_trade_by_id(trade_id, user_id) or {}
    if not trade:
        st.error("Trade not found.")
        if st.button("← Back to Trades"):
            st.switch_page("pages/trades.py")
        st.stop()

loaded_state = trade.get("state") if trade else None

# --- Заголовок ---
if is_new_trade:
    st.title("New trade")
else:
    asset = (trade.get("asset") or "Trade").strip()
    d = parse_date(trade.get("date_local"))
    t = parse_time(trade.get("time_local"))
    date_str = d.strftime("%d.%m.%Y") if d else ""
    time_str = t.strftime("%H:%M") if t else ""
    st.title(f"{asset} · {date_str} - {time_str}")

# Placeholder для ошибок — невидим когда пуст
message_placeholder = st.empty()

# --- Ключ состояния виджетов ---
state_key = f"{TM_KEY_PREFIX}{trade_id or 'new'}"

# --- Загружаем данные ---
assets = get_setting("assets", ASSETS_VALUES)
account_rows = cached_accounts(user_id, True)
accounts = to_option_format(
    account_rows, formatter=lambda acc: f"{acc['name']}")
setups = to_option_format(cached_setups(
    user_id), formatter=lambda s: f"{s['name']}")
analyses = to_option_format(
    cached_analysis(user_id),
    formatter=lambda a: f"{a.get('date_local')} · {a.get('asset')}",
)
defaults = get_trade_defaults(trade, accounts)
charts = list_charts(trade_id=trade_id) if trade_id else []
base_trade_notes = list_trade_notes(trade_id) if trade_id else []


def _get_account_id_by_label(label: str) -> Optional[int]:
    for acc in account_rows:
        if acc.get("name") == label:
            return acc.get("id")
    return None


def _get_account_balance(acc_id: Optional[int]) -> Optional[float]:
    if acc_id is None:
        return None
    for acc in account_rows:
        if acc.get("id") == acc_id:
            starting_balance = acc.get("starting_balance")
            try:
                return float(starting_balance) if starting_balance is not None else None
            except (TypeError, ValueError):
                return None
    return None


def _calculate_rewards() -> None:
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
    account_id_val = _get_account_id_by_label(account["label"])
    account_balance = _get_account_balance(account_id_val)
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
        st.session_state[widget_keys["risk_reward"]] = round(
            net_pnl / (account_balance * (risk_pct / 100)), 2
        )
        st.session_state[widget_keys["reward_percent"]] = round(
            (net_pnl / account_balance) * 100, 2
        )


# Диалог подтверждения удаления
if st.session_state.get("_te_pending_delete"):
    @st.dialog("Delete trade")
    def _confirm_delete() -> None:
        st.warning("Delete this trade? This cannot be undone.")
        c1, c2 = st.columns(2)
        if c1.button("Delete", type="primary", width="stretch"):
            try:
                delete_trade(st.session_state["_te_pending_delete"], user_id)
                clear_note_selector_state(f"{state_key}_note_selector")
            except Exception as exc:
                st.toast(f"Failed to delete: {exc}", icon="❌")
            st.session_state.pop("_te_pending_delete", None)
            st.cache_data.clear()
            st.switch_page("pages/trades.py")
        if c2.button("Cancel", width="stretch"):
            st.session_state.pop("_te_pending_delete", None)
            st.rerun()

    _confirm_delete()

# --- Форма: чарты (слева) + секции (справа) ---
side_col, stages_col = st.columns([2, 1])

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
        previous_dialog_name=None,
        excerpt_limit=120,
    )

with stages_col:
    # State navigation: кнопки ← selectbox →
    _state_nav_key = f"{state_key}_state_idx"
    _current_state = trade.get("state")
    allowed_states = get_allowed_states(_current_state)
    if _state_nav_key not in st.session_state:
        st.session_state[_state_nav_key] = (
            allowed_states.index(
                _current_state) if _current_state in allowed_states else 0
        )
    _state_idx = max(
        0, min(st.session_state[_state_nav_key], len(allowed_states) - 1))
    _prev_col, _sel_col, _next_col = st.columns(
        [1, 6, 1], vertical_alignment="bottom")
    if _prev_col.button("←", disabled=(_state_idx == 0), key=f"{state_key}_state_prev", width="stretch"):
        st.session_state[_state_nav_key] = _state_idx - 1
        st.rerun()
    if _next_col.button("→", disabled=(_state_idx == len(allowed_states) - 1), key=f"{state_key}_state_next", width="stretch"):
        st.session_state[_state_nav_key] = _state_idx + 1
        st.rerun()
    selected_state = _sel_col.selectbox(
        "Trade state",
        allowed_states,
        index=_state_idx,
    )
    st.session_state[_state_nav_key] = allowed_states.index(selected_state)

    visible = visible_stages(selected_state)
    outcome_visible = "outcome" in visible
    locked_from_analysis = st.session_state.get(
        f"{TM_DEFAULT_PREFIX}analysis") is not None

    main_values = render_main_stage(
        expanded=(selected_state == "Open"),
        defaults=defaults["open"],
        account_options=accounts,
        analysis_options=analyses,
        setup_options=setups,
        state_key=f"{state_key}_main",
        on_risk_change=_calculate_rewards,
        locked_fields=locked_from_analysis,
        assets=assets,
        user_tz=trade.get("local_tz") or get_setting("local_tz", LOCAL_TZ),
    )

    outcome_values = render_outcome_stage(
        visible=outcome_visible,
        expanded=(selected_state == "Outcome"),
        defaults=defaults["outcome"],
        state_key=f"{state_key}_outcome",
        is_missed=main_values["is_missed"],
        on_change=_calculate_rewards,
    )

    review_values = render_review_stage(
        visible="review" in visible,
        expanded=(selected_state == "Reviewed"),
        defaults=defaults["review"],
        state_key=f"{state_key}_review",
    )

# --- Нижняя панель actions ---
btn_back, btn_save, btn_delete, _ = st.columns([0.1, 0.1, 0.12, 0.68])
if btn_back.button("← Trades", width="stretch"):
    st.switch_page("pages/trades.py")
submitted = btn_save.button("Save", type="primary", width="stretch")
if not is_new_trade:
    if btn_delete.button("Delete", type="secondary", width="stretch"):
        st.session_state["_te_pending_delete"] = trade_id
        st.rerun()

# --- Сохранение ---
if submitted:
    if not main_values["asset"]:
        message_placeholder.error("Select an asset.")
        st.stop()
    if not main_values["account"]:
        message_placeholder.error("Select an account.")
        st.stop()
    if selected_state == "Outcome":
        if not outcome_values:
            message_placeholder.error('Fill in the "Outcome" block.')
            st.stop()
        if outcome_values["net_pnl"] is None:
            message_placeholder.error("Provide Net PnL.")
            st.stop()
    if selected_state == "Reviewed":
        if review_values and review_values["estimation"] == 0 and not (review_values.get("cold_thoughts") or "").strip():
            message_placeholder.error(
                "Fill in Cold thoughts when trade has mistake.")
            st.stop()

    local_tz = trade.get("local_tz") or get_setting("local_tz", LOCAL_TZ)
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
            "hot_thoughts": (outcome_values["hot_thoughts"] or "").strip() or None,
        })

    if review_values:
        payload.update({
            "cold_thoughts": (review_values["cold_thoughts"] or "").strip() or None,
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
                if is_new_trade:
                    payload["local_tz"] = local_tz
                    current_trade_id = create_trade(
                        user_id, payload, conn=conn)
                else:
                    update_trade(current_trade_id, user_id, payload, conn=conn)

                persist_chart_editor(
                    attached_charts=charts,
                    editor_rows=current_charts,
                    conn=conn,
                    attach_chart=lambda chart_id, tid=current_trade_id: attach_chart_to_trade(
                        tid, chart_id, conn=conn
                    ),
                )
                for note_id in base_note_ids - staged_note_ids_set:
                    detach_note_from_trade(
                        current_trade_id, note_id, conn=conn)
                for note_id in staged_note_ids_set - base_note_ids:
                    attach_note_to_trade(current_trade_id, note_id, conn=conn)

        # Очистка состояния дефолтов
        st.session_state.pop(f"{TM_DEFAULT_PREFIX}analysis", None)
        st.session_state.pop(f"{TM_DEFAULT_PREFIX}asset", None)
        clear_note_selector_state(f"{state_key}_note_selector")
        st.cache_data.clear()
        st.toast("Trade saved." if not is_new_trade else "Trade created.", icon="🔥")
        if is_new_trade:
            st.query_params["id"] = str(current_trade_id)
        st.rerun()
    except Exception as exc:
        message_placeholder.error(f"Failed to save the trade: {exc}")

# --- Диалог заметок (одиночный уровень — допустимо на странице) ---
render_note_manager()
