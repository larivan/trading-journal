"""Страница редактирования/создания трейда."""

import json
from datetime import date, datetime as _dt
from typing import Any, Dict, Optional

import streamlit as st
from streamlit_chat_prompt import prompt as chat_prompt

from components.editor_ui import (
    render_delete_dialog,
    render_editor_actions,
    render_entry_card,
    section_divider,
)
from components.image_editor import persist_image_editor, render_image_editor
from components.trade_manager.defaults import get_trade_defaults
from components.trade_manager.sections import (
    render_main_stage,
    render_outcome_stage,
    render_review_stage,
)
from config import (
    ASSETS_VALUES,
    DEFAULT_MISTAKE_TYPES,
    LOCAL_TZ,
    TM_KEY_PREFIX,
    TM_DEFAULT_PREFIX,
)
from db import (
    add_image,
    attach_image_to_note,
    attach_image_to_trade,
    attach_note_to_trade,
    count_notes_by_trade,
    create_note,
    create_trade,
    delete_note,
    delete_trade,
    detach_note_from_trade,
    update_note,
    get_trade_by_id,
    list_images,
    list_notes,
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
if "_new_trade_id" in st.session_state:
    st.query_params["id"] = str(st.session_state.pop("_new_trade_id"))
    st.rerun()
trade_id_str = params.get("id")
trade_id: Optional[int] = int(trade_id_str) if trade_id_str else None
is_new_trade = trade_id is None

# --- Загружаем трейд из БД ---
trade: Dict[str, Any] = {}
if not is_new_trade:
    trade = get_trade_by_id(trade_id, user_id) or {}
    if not trade:
        st.error("Trade not found.")
        if st.button("← Back"):
            back_page = st.session_state.pop("_back_page", "pages/trades.py")
            back_params = st.session_state.pop("_back_params", {})
            if back_params:
                st.session_state["_returning_params"] = back_params
            st.switch_page(back_page)
        st.stop()

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
mistake_type_options = get_setting("mistake_types", DEFAULT_MISTAKE_TYPES)
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
images = list_images(trade_id=trade_id) if trade_id else []


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
        "is_missed": f"{state_key}_is_missed",
        "net_pnl": f"{state_key}_outcome_net_pnl",
        "risk_reward": f"{state_key}_outcome_risk_reward",
        "reward_percent": f"{state_key}_outcome_reward_percent",
    }
    risk_pct = st.session_state.get(widget_keys["risk_pct"])
    is_missed_raw = st.session_state.get(widget_keys["is_missed"])
    is_missed = (is_missed_raw == "Missed") if isinstance(
        is_missed_raw, str) else bool(is_missed_raw)
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
        hypothetical = round(
            account_balance * (risk_pct / 100) * risk_reward, 2)
        st.session_state[widget_keys["net_pnl"]] = hypothetical
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


def _chart_images_changed(db_images: list, editor_images: list) -> bool:
    """Возвращает True, если состояние редактора отличается от БД."""
    db_by_id = {img["id"]: img for img in db_images}
    editor_by_id: dict = {}
    for row in editor_images:
        iid = row.get("id")
        url = (row.get("image_url") or "").strip()
        if iid is None and url:
            return True  # новое изображение
        if iid is not None:
            editor_by_id[iid] = row
    if set(db_by_id) != set(editor_by_id):
        return True  # удалено одно или несколько
    for iid, db_row in db_by_id.items():
        ed_row = editor_by_id.get(iid)
        if ed_row is None:
            return True
        if (ed_row.get("caption") or "") != (db_row.get("caption") or ""):
            return True
    return False


def _on_status_change() -> None:
    key = f"{state_key}_is_missed"
    if st.session_state.get(key) is None:
        st.session_state[key] = "Taken"
    _calculate_rewards()


# Диалог подтверждения удаления
render_delete_dialog(
    pending_key="_te_pending_delete",
    entity_label="trade",
    delete_fn=delete_trade,
    user_id=user_id,
    redirect_page="pages/trades.py",
)

_NOTE_CATEGORIES = ["Hot thought", "Cold thought", "Observation"]

# --- Форма: чарты/комментарии (слева) + секции (справа) ---
side_col, stages_col = st.columns([2, 1], gap="medium")

with side_col:
    st.markdown("#### Charts")
    current_images = render_image_editor(
        key=f"{state_key}_chart_editor",
        base_rows=images,
        layout_columns=2,
    )

    if trade_id and _chart_images_changed(images, current_images):
        with transaction() as conn:
            persist_image_editor(
                attached_images=images,
                editor_rows=current_images,
                attach_image=lambda iid, c=conn: attach_image_to_trade(trade_id, iid, conn=c),
                conn=conn,
            )
        st.cache_data.clear()
        st.rerun()

    st.markdown("#### Comments")
    trade_notes = list_trade_notes(trade_id) if trade_id else []
    note_counts = count_notes_by_trade(user_id) if trade_id else {}

    if not trade_notes:
        with st.container(border=True):
            st.caption("No comments yet. Send your first one below.")
    else:
        for note in trade_notes:
            time_display = (note.get("time_local") or "")[:5]
            category = note.get("category") or "—"
            count = note_counts.get(note["id"], 1)
            is_shared = count > 1
            shared_badge = f"  ·  🔗 {count} trades" if is_shared else ""
            badge = f"{note.get('date_local', '')}  {time_display}  ·  {category}{shared_badge}"
            note_images = list_images(note_id=note["id"])
            render_entry_card(
                entry_id=note["id"],
                badge=badge,
                time_display="",
                body=note.get("body") or "",
                images=note_images,
                on_save=lambda new_body, nid=note["id"]: update_note(nid, user_id, {"body": new_body}),
                on_delete=lambda nid=note["id"], shared=is_shared: (
                    detach_note_from_trade(trade_id, nid) if shared
                    else delete_note(nid, user_id)
                ),
                delete_help="Remove from this trade" if is_shared else "Delete",
                key_prefix="tnote",
            )

    if trade_id:
        _all_notes = list_notes(user_id, {"exclude_analysis": True})
        _attached_ids = {n["id"] for n in trade_notes}
        _linkable = [n for n in _all_notes if n["id"] not in _attached_ids]
        if _linkable:
            with st.expander("Link existing observation"):
                _search_key = f"_link_search_{state_key}"
                _search = st.text_input("", key=_search_key,
                                        placeholder="Search...",
                                        label_visibility="collapsed")
                _visible = [
                    n for n in _linkable
                    if not _search or _search.lower() in (n.get("body") or "").lower()
                ][:15]
                for ln in _visible:
                    c_text, c_btn = st.columns([0.9, 0.1])
                    _ln_count = note_counts.get(ln["id"], 0)
                    _meta = f"{ln.get('date_local') or ''}  ·  {ln.get('category') or '—'}"
                    if _ln_count > 0:
                        _meta += f"  ·  🔗 {_ln_count} {'trade' if _ln_count == 1 else 'trades'}"
                    c_text.caption(_meta)
                    c_text.markdown((ln.get("body") or "")[:80])
                    if c_btn.button("🔗", key=f"_link_note_{ln['id']}", use_container_width=True):
                        attach_note_to_trade(trade_id, ln["id"])
                        st.cache_data.clear()
                        st.rerun()

    st.divider()

    _cat_key = f"_note_cat_{state_key}"
    if _cat_key not in st.session_state:
        st.session_state[_cat_key] = "Hot thought"

    def _on_category_change() -> None:
        if st.session_state[_cat_key] is None:
            st.session_state[_cat_key] = "Hot thought"

    selected_category = st.pills(
        "Category",
        _NOTE_CATEGORIES,
        key=_cat_key,
        on_change=_on_category_change,
        label_visibility="collapsed",
    )

    response = chat_prompt(
        name=f"obs_{state_key}",
        key=f"obs_{state_key}",
        placeholder="Write a comment...",
        main_bottom=False,
    )
    if response and (response.text or response.images):
        if is_new_trade:
            st.warning("Save the trade first to add comments.")
        else:
            body = (response.text or "").strip() or "(image)"
            note_payload = {
                "body": body,
                "category": selected_category or "Observation",
                "date_local": date.today().isoformat(),
                "time_local": _dt.now().strftime("%H:%M:%S"),
            }
            with transaction() as conn:
                new_note_id = create_note(user_id, note_payload, conn=conn)
                attach_note_to_trade(trade_id, new_note_id, conn=conn)
                for img in (response.images or []):
                    data_uri = f"data:{img.type};{img.format},{img.data}"
                    image_id = add_image(data_uri, conn=conn)
                    attach_image_to_note(new_note_id, image_id, conn=conn)
            st.cache_data.clear()
            st.rerun()

with stages_col:
    # Taken / Missed toggle — всегда вверху
    _is_missed_key = f"{state_key}_is_missed"
    if _is_missed_key not in st.session_state:
        st.session_state[_is_missed_key] = "Missed" if defaults.get(
            "is_missed") else "Taken"
    is_missed_option = st.segmented_control(
        "Trade status",
        ["Taken", "Missed"],
        key=_is_missed_key,
        on_change=_on_status_change,
        width="stretch",
        label_visibility="collapsed",
    )
    is_missed = int(is_missed_option == "Missed") if is_missed_option else 0

    section_divider()
    st.caption("ENTRY")

    locked_from_analysis = st.session_state.get(
        f"{TM_DEFAULT_PREFIX}analysis") is not None

    main_values = render_main_stage(
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

    section_divider()
    st.caption("OUTCOME")

    outcome_values = render_outcome_stage(
        defaults=defaults["outcome"],
        state_key=f"{state_key}_outcome",
        is_missed=is_missed,
        on_change=_calculate_rewards,
    )

    section_divider()
    st.caption("REVIEW")

    review_values = render_review_stage(
        defaults=defaults["review"],
        state_key=f"{state_key}_review",
        mistake_type_options=mistake_type_options,
    )

    st.divider()
    submitted = render_editor_actions(
        is_new=is_new_trade,
        pending_delete_key="_te_pending_delete",
        entity_id=trade_id,
        default_back_page="pages/trades.py",
    )

# --- Сохранение ---
if submitted:
    if not main_values["asset"]:
        message_placeholder.error("Select an asset.")
        st.stop()
    if not main_values["account"]:
        message_placeholder.error("Select an account.")
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
        "trade_type": main_values.get("trade_type"),
        "analysis_id": main_values["analysis"],
        "setup_id": main_values["setup"],
        "risk_pct": float(main_values["risk_pct"]),
        "session": session_value,
        "is_missed": is_missed,
    }

    # Outcome: сохраняем только если явно задано
    original_net_pnl = trade.get("net_pnl")
    if (
        original_net_pnl is not None
        or (not is_missed and outcome_values["net_pnl"] != 0.0)
        or (is_missed and outcome_values["risk_reward"] != 0.0)
    ):
        payload.update({
            "net_pnl": outcome_values["net_pnl"],
            "risk_reward": outcome_values["risk_reward"],
            "reward_percent": outcome_values["reward_percent"],
        })

    # Review: сохраняем is_correct и mistake_types всегда (None = не ревьювирован)
    payload["is_correct"] = review_values.get("is_correct")
    if review_values.get("is_correct") is not None:
        payload["mistake_types"] = json.dumps(
            review_values.get("mistake_types") or [])
    else:
        payload["mistake_types"] = json.dumps([])

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

                persist_image_editor(
                    attached_images=images,
                    editor_rows=current_images,
                    conn=conn,
                    attach_image=lambda image_id, tid=current_trade_id: attach_image_to_trade(
                        tid, image_id, conn=conn
                    ),
                )

        # Очистка состояния дефолтов
        st.session_state.pop(f"{TM_DEFAULT_PREFIX}analysis", None)
        st.session_state.pop(f"{TM_DEFAULT_PREFIX}asset", None)
        st.cache_data.clear()
        st.toast("Trade saved." if not is_new_trade else "Trade created.", icon="🔥")
        if is_new_trade:
            st.query_params["id"] = str(current_trade_id)
        st.rerun()
    except Exception as exc:
        message_placeholder.error(f"Failed to save the trade: {exc}")
