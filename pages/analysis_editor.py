"""Страница редактирования/создания дневного анализа."""

from datetime import date, datetime as _dt
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
from streamlit_chat_prompt import prompt as chat_prompt

from config import (
    ANALYSIS_MANAGER_KEY_PREFIX,
    ASSETS_VALUES,
    DAILY_BIAS_VALUES,
    LOCAL_TZ,
)
from db import (
    add_analysis,
    add_analysis_stage,
    add_image,
    attach_image_to_analysis_stage,
    count_notes_by_analysis,
    create_trade,
    delete_analysis,
    delete_analysis_stage,
    delete_note,
    detach_note_from_analysis,
    update_analysis_stage,
    update_note,
    get_analysis,
    list_analysis_notes,
    list_analysis_stages,
    list_images,
    list_trades,
    transaction,
    update_analysis,
)
from components.editor_ui import (
    render_delete_dialog,
    render_editor_actions,
    render_entry_card,
    section_divider,
)
from helpers import calculate_trade_result, custom_selectbox, parse_date, to_option_format
from utils.auth import get_current_user_id, get_setting
from utils.cached_data import cached_accounts, cached_setups
from utils.trade_sessions import detect_trade_session

st.set_page_config(layout="wide")

user_id = get_current_user_id()

# --- Читаем analysis_id из URL-параметров ---
params = st.query_params
if "_returning_params" in st.session_state:
    for k, v in st.session_state.pop("_returning_params").items():
        st.query_params[k] = v
    st.rerun()
if "_new_analysis_id" in st.session_state:
    st.query_params["id"] = str(st.session_state.pop("_new_analysis_id"))
    st.rerun()
analysis_id_str = params.get("id")
analysis_id: Optional[int] = int(analysis_id_str) if analysis_id_str else None
is_new_analysis = analysis_id is None

# --- Загружаем анализ из БД ---
analysis: Dict[str, Any] = {}
if not is_new_analysis:
    analysis = get_analysis(analysis_id, user_id) or {}
    if not analysis:
        st.error("Analysis not found.")
        if st.button("← Back"):
            back_page = st.session_state.pop("_back_page", "pages/analysis.py")
            back_params = st.session_state.pop("_back_params", {})
            if back_params:
                st.session_state["_returning_params"] = back_params
            st.switch_page(back_page)
        st.stop()

# --- Заголовок ---
if is_new_analysis:
    st.title("New analysis")
else:
    asset = (analysis.get("asset") or "Analysis").strip() or "Analysis"
    date_value = (analysis.get("date_local") or "").strip() or ""
    st.title(f"{asset} · {date_value}" if date_value else asset)

message_placeholder = st.empty()
sk = f"{ANALYSIS_MANAGER_KEY_PREFIX}{analysis_id or 'new'}"

# --- Загрузка данных ---
assets = get_setting("assets", ASSETS_VALUES)
local_tz = get_setting("local_tz", LOCAL_TZ)
analysis_stages: List[Dict[str, Any]] = []
analysis_notes: List[Dict[str, Any]] = []
note_counts: Dict[int, int] = {}

if not is_new_analysis:
    analysis_stages = list_analysis_stages(
        user_id, {"analysis_id": analysis_id})
    analysis_notes = list_analysis_notes(analysis_id)
    note_counts = count_notes_by_analysis(user_id)

# --- Диалог подтверждения удаления ---
render_delete_dialog(
    pending_key="_ae_pending_delete",
    entity_label="analysis",
    delete_fn=delete_analysis,
    user_id=user_id,
    redirect_page="pages/analysis.py",
)


# =====================================================================
# Макет: левая колонка (Journal) | правая (мета + трейды)
# =====================================================================

side_col, meta_col = st.columns([2, 1], gap="medium")

with side_col:
    st.markdown("#### Journal")

    # --- Объединённая лента: stages + notes, сортировка по времени ---
    entries: List[Dict[str, Any]] = []
    for s in analysis_stages:
        entries.append({"_kind": "stage", **s})
    for n in analysis_notes:
        entries.append({"_kind": "note", **n})
    entries.sort(key=lambda e: (e.get("time_local") or ""))

    if not entries:
        with st.container(border=True):
            st.caption("No entries yet.")
    else:
        _STAGE_LABEL = {
            "pre-market": "Pre-Market",
            "plan": "Plan",
            "post-market": "Post-Market",
        }
        for entry in entries:
            kind = entry["_kind"]
            if kind == "stage":
                badge = "[" + _STAGE_LABEL.get(entry.get("type", ""), entry.get("type", "")) + "]"
                time_display = (entry.get("time_local") or "")[:5]
                stage_images = list_images(analysis_stage_id=entry["id"])
                render_entry_card(
                    entry_id=entry["id"],
                    badge=badge,
                    time_display=time_display,
                    body=entry.get("summary") or "",
                    images=stage_images,
                    on_save=lambda new_body, eid=entry["id"]: update_analysis_stage(eid, {"summary": new_body}),
                    on_delete=lambda eid=entry["id"]: delete_analysis_stage(eid),
                    key_prefix="stage",
                )
            else:  # note
                count = note_counts.get(entry["id"], 1)
                is_shared = count > 1
                badge_extra = f"  ·  🔗 {count} analyses" if is_shared else ""
                time_display = (entry.get("time_local") or "")[:5]
                note_images = list_images(note_id=entry["id"])
                render_entry_card(
                    entry_id=entry["id"],
                    badge=f"[Note]{badge_extra}",
                    time_display=time_display,
                    body=entry.get("body") or "",
                    images=note_images,
                    on_save=lambda new_body, eid=entry["id"]: update_note(eid, user_id, {"body": new_body}),
                    on_delete=lambda eid=entry["id"], shared=is_shared: (
                        detach_note_from_analysis(analysis_id, eid) if shared
                        else delete_note(eid, user_id)
                    ),
                    delete_help="Remove from this analysis" if is_shared else "Delete",
                    key_prefix="anote",
                )

    # --- Один chat_prompt с pills выбора типа ---
    _STAGE_TYPE_ORDER = {"pre-market": 0, "plan": 1, "post-market": 2}
    _STAGE_LABEL_MAP = [("Pre-Market", "pre-market"), ("Plan", "plan"), ("Post-Market", "post-market")]
    _existing_orders = [
        _STAGE_TYPE_ORDER[s["type"]]
        for s in analysis_stages
        if s.get("type") in _STAGE_TYPE_ORDER
    ]
    _min_order = max(_existing_orders) if _existing_orders else 0
    _available_pills = [
        label for label, key in _STAGE_LABEL_MAP
        if _STAGE_TYPE_ORDER[key] >= _min_order
    ]

    _type_key = f"{sk}_entry_type"
    if st.session_state.get(_type_key) not in _available_pills:
        st.session_state[_type_key] = _available_pills[0]

    st.pills(
        "Type",
        _available_pills,
        key=_type_key,
        label_visibility="collapsed",
    )

    resp = chat_prompt(
        name=f"journal_{sk}",
        key=f"journal_{sk}",
        placeholder="Add entry...",
        main_bottom=False,
    )

    if resp and (resp.text or resp.images):
        if is_new_analysis:
            st.warning("Save the analysis first to add entries.")
        else:
            entry_type = st.session_state.get(_type_key, "Pre-Market")
            _type_map = {
                "Pre-Market": "pre-market",
                "Plan": "plan",
                "Post-Market": "post-market",
            }
            with transaction() as conn:
                stage_id = add_analysis_stage(
                    {
                        "analysis_id": analysis_id,
                        "type": _type_map[entry_type],
                        "summary": (resp.text or "").strip() or "(image)",
                        "time_local": _dt.now().strftime("%H:%M:%S"),
                    },
                    conn=conn,
                )
                for img in (resp.images or []):
                    data_uri = f"data:{img.type};{img.format},{img.data}"
                    image_id = add_image(data_uri, conn=conn)
                    attach_image_to_analysis_stage(
                        stage_id, image_id, conn=conn)
            st.cache_data.clear()
            st.rerun()

# --- Мета-колонка ---
with meta_col:
    # Дата
    _default_date = parse_date(analysis.get("date_local")) or date.today()
    date_val = st.date_input("Date", value=_default_date,
                             key=f"{sk}_date", format="DD.MM.YYYY")

    # Актив
    _asset_val = analysis.get("asset") or ""
    _asset_idx = assets.index(_asset_val) if _asset_val in assets else None
    asset_val = st.selectbox(
        "Asset",
        assets,
        index=_asset_idx,
        placeholder="Select asset...",
        key=f"{sk}_asset",
    )

    section_divider()
    st.caption("PRE-MARKET")

    _daily_key = f"{sk}_daily_bias"
    if _daily_key not in st.session_state:
        st.session_state[_daily_key] = analysis.get("daily_bias")

    daily_bias = st.pills(
        "Daily bias",
        DAILY_BIAS_VALUES,
        key=_daily_key,
        label_visibility="collapsed",
    )

    section_divider()
    st.caption("POST-MARKET")

    _fact_key = f"{sk}_fact_bias"
    if _fact_key not in st.session_state:
        st.session_state[_fact_key] = analysis.get("fact_bias")

    fact_bias = st.pills(
        "Fact bias",
        DAILY_BIAS_VALUES,
        key=_fact_key,
        label_visibility="collapsed",
    )

# --- Нижняя панель actions ---
st.divider()
submitted = render_editor_actions(
    is_new=is_new_analysis,
    pending_delete_key="_ae_pending_delete",
    entity_id=analysis_id,
    default_back_page="pages/analysis.py",
)

# --- Секция трейдов (под actions, отдельный раздел) ---
if not is_new_analysis:
    st.divider()
    st.caption("TRADES")

    account_rows_all = cached_accounts(user_id)
    setup_rows_all = cached_setups(user_id)
    accounts_options = to_option_format(
        account_rows_all, formatter=lambda a: a.get("name", ""))
    account_map = {a["id"]: a["name"] for a in account_rows_all}
    setup_map = {s["id"]: s["name"] for s in setup_rows_all}
    _default_acc_row = next(
        (a for a in account_rows_all if not a.get("is_archived")), None)
    _default_acc = _default_acc_row["id"] if _default_acc_row else None

    trade_rows = list_trades(user_id, {"analysis_id": analysis_id})
    if trade_rows:
        df_exec = pd.DataFrame(trade_rows)
        df_exec["result"] = df_exec.apply(
            lambda r: calculate_trade_result(r.get("risk_reward"), r.get("is_missed")), axis=1
        )
        df_exec["_link"] = "/trade_editor?id=" + df_exec["id"].astype(str)
        df_exec["account_name"] = df_exec["account_id"].map(account_map)
        df_exec["setup_name"] = df_exec["setup_id"].map(setup_map)
        df_exec["execution"] = df_exec["is_correct"].map({1: "✓", 0: "✗"})
        display_cols = [
            "_link", "date_local", "session", "asset", "trade_type",
            "account_name", "setup_name", "status", "result",
            "net_pnl", "risk_reward", "reward_percent", "execution",
        ]
        for col in display_cols:
            if col not in df_exec.columns:
                df_exec[col] = None
        st.dataframe(
            df_exec[display_cols],
            column_config={
                "_link": st.column_config.LinkColumn("", display_text="Open →"),
                "date_local": st.column_config.TextColumn("Date"),
                "session": st.column_config.TextColumn("Session"),
                "asset": st.column_config.TextColumn("Asset"),
                "trade_type": st.column_config.TextColumn("Type"),
                "account_name": st.column_config.TextColumn("Account"),
                "setup_name": st.column_config.TextColumn("Setup"),
                "status": st.column_config.TextColumn("Status"),
                "result": st.column_config.TextColumn("Result"),
                "net_pnl": st.column_config.NumberColumn("PnL"),
                "risk_reward": st.column_config.NumberColumn("R:R"),
                "reward_percent": st.column_config.NumberColumn("R%", format="%.2f%%"),
                "execution": st.column_config.TextColumn("Exec"),
            },
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No trades yet.")

    btn_create_trade, _ = st.columns([0.12, 0.88])
    with btn_create_trade.popover("Create trade", type="primary", width="stretch"):
        if not account_rows_all:
            st.error("Create an account first.")
        else:
            pop_account = custom_selectbox(
                "Account",
                accounts_options,
                value=_default_acc,
                key=f"{sk}_pop_account",
            )
            if st.button("Go", type="primary", width=250, key=f"{sk}_pop_go"):
                _now = _dt.now()
                with transaction() as conn:
                    new_id = create_trade(user_id, {
                        "date_local": _now.date().isoformat(),
                        "time_local": _now.strftime("%H:%M:%S"),
                        "account_id": pop_account,
                        "asset": asset_val or "",
                        "analysis_id": analysis_id,
                        "session": detect_trade_session(
                            _now.date(),
                            _now.time(),
                            local_tz_label=local_tz,
                        ),
                        "local_tz": local_tz,
                        "is_missed": 0,
                    }, conn=conn)
                st.cache_data.clear()
                st.session_state["_new_trade_id"] = new_id
                st.session_state["_back_page"] = "pages/analysis_editor.py"
                st.session_state["_back_params"] = {"id": str(analysis_id)}
                st.switch_page("pages/trade_editor.py")

# --- Сохранение ---
if submitted:
    if not asset_val:
        message_placeholder.error("Select an asset.")
        st.stop()

    # Авто-вычисление state
    all_stages = list_analysis_stages(
        user_id, {"analysis_id": analysis_id}) if not is_new_analysis else []
    stage_types = {s["type"] for s in all_stages}
    trade_rows_for_state = list_trades(
        user_id, {"analysis_id": analysis_id}) if not is_new_analysis else []
    trade_count = len(trade_rows_for_state)
    computed_state = (
        "post-market" if "post-market" in stage_types else
        "execution" if trade_count > 0 else
        "plan" if "plan" in stage_types else
        "pre-market"
    )

    # Авто-вычисление day_result из net_pnl трейдов
    completed = [
        t for t in trade_rows_for_state
        if t.get("net_pnl") is not None and not t.get("is_missed")
    ]
    if completed:
        total_pnl = sum(t["net_pnl"] for t in completed)
        computed_day_result = "profit" if total_pnl > 0 else "loss" if total_pnl < 0 else "null"
    else:
        computed_day_result = None

    payload: Dict[str, Any] = {
        "date_local": date_val.isoformat(),
        "asset": asset_val,
        "daily_bias": daily_bias,
        "fact_bias": fact_bias,
        "day_result": computed_day_result,
        "state": computed_state,
    }

    try:
        with transaction() as conn:
            if is_new_analysis:
                current_analysis_id = add_analysis(user_id, payload, conn=conn)
            else:
                update_analysis(analysis_id, user_id, payload, conn=conn)
                current_analysis_id = analysis_id

        st.cache_data.clear()
        st.toast(
            "Analysis saved." if not is_new_analysis else "Analysis created.", icon="🔥")
        if is_new_analysis:
            st.query_params["id"] = str(current_analysis_id)
        st.rerun()
    except Exception as exc:
        message_placeholder.error(f"Failed to save analysis: {exc}")
