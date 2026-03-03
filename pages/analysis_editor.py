"""Страница редактирования/создания дневного анализа."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from components.analysis_manager.defaults import build_analysis_defaults
from components.analysis_manager.sections import (
    render_plan_section,
    render_post_stage,
    render_pre_stage,
)
from components.analysis_manager.state import get_allowed_analysis_stages
from components.chart_editor import persist_chart_editor
from components.note_manager import render_note_manager
from components.note_selector import clear_note_selector_state
from config import (
    ANALYSIS_STATE_VALUES,
    ANALYSIS_MANAGER_KEY_PREFIX,
    TM_DEFAULT_PREFIX,
)
from db import (
    add_analysis,
    add_analysis_stage,
    attach_chart_to_analysis_stage,
    attach_note_to_analysis_stage,
    delete_analysis,
    delete_analysis_stage,
    detach_note_from_analysis_stage,
    get_analysis,
    list_trades,
    transaction,
    update_analysis,
    update_analysis_stage,
)
from helpers import parse_date
from utils.auth import get_current_user_id

st.set_page_config(layout="wide")

user_id = get_current_user_id()

# --- Читаем analysis_id из URL-параметров ---
params = st.query_params
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
        if st.button("← Back to Analysis"):
            st.switch_page("pages/analysis.py")
        st.stop()

# --- Заголовок ---
if is_new_analysis:
    st.title("New analysis")
else:
    asset = (analysis.get("asset") or "Analysis").strip() or "Analysis"
    date_value = (analysis.get("date_local") or "").strip() or ""
    st.title(f"{asset} · {date_value}" if date_value else asset)

# Placeholder для ошибок — невидим когда пуст
message_placeholder = st.empty()

# --- Ключ состояния виджетов ---
state_key = f"{ANALYSIS_MANAGER_KEY_PREFIX}{analysis_id or 'new'}"

defaults = build_analysis_defaults(analysis)


def _visible_stage_types(current_stage: str) -> List[str]:
    if current_stage not in ANALYSIS_STATE_VALUES:
        return [ANALYSIS_STATE_VALUES[0]]
    idx = ANALYSIS_STATE_VALUES.index(current_stage)
    return ANALYSIS_STATE_VALUES[: idx + 1]


# Analysis stage selectbox with navigation: кнопки ← selectbox →
_stage_nav_key = f"{state_key}_stage_idx"
current_stage = analysis.get("state") or ANALYSIS_STATE_VALUES[0]
allowed_stages = get_allowed_analysis_stages(current_stage)
if _stage_nav_key not in st.session_state:
    st.session_state[_stage_nav_key] = (
        allowed_stages.index(current_stage) if current_stage in allowed_stages else 0
    )
_stage_idx = max(0, min(st.session_state[_stage_nav_key], len(allowed_stages) - 1))
_prev_col, _sel_col, _next_col = st.columns([1, 6, 1], vertical_alignment="bottom")
if _prev_col.button("←", disabled=(_stage_idx == 0), key=f"{state_key}_stage_prev"):
    st.session_state[_stage_nav_key] = _stage_idx - 1
    st.rerun()
if _next_col.button("→", disabled=(_stage_idx == len(allowed_stages) - 1), key=f"{state_key}_stage_next"):
    st.session_state[_stage_nav_key] = _stage_idx + 1
    st.rerun()
selected_stage = _sel_col.selectbox(
    "Analysis stage",
    allowed_stages,
    index=_stage_idx,
)
st.session_state[_stage_nav_key] = allowed_stages.index(selected_stage)

# Диалог подтверждения удаления
if st.session_state.get("_ae_pending_delete"):
    @st.dialog("Delete analysis")
    def _confirm_delete() -> None:
        st.warning("Delete this analysis? This cannot be undone.")
        c1, c2 = st.columns(2)
        if c1.button("Delete", type="primary", width="stretch"):
            try:
                delete_analysis(
                    st.session_state["_ae_pending_delete"], user_id)
            except Exception as exc:
                st.toast(f"Failed to delete: {exc}", icon="❌")
            st.session_state.pop("_ae_pending_delete", None)
            st.cache_data.clear()
            st.switch_page("pages/analysis.py")
        if c2.button("Cancel", width="stretch"):
            st.session_state.pop("_ae_pending_delete", None)
            st.rerun()

    _confirm_delete()

visible = _visible_stage_types(selected_stage)

pre_analysis_values, pre_values = render_pre_stage(
    stage_data=defaults["stages"].get("pre-market"),
    analysis_defaults=defaults["analysis"],
    visible="pre-market" in visible,
    expanded=(selected_stage == "pre-market"),
    state_key=f"{state_key}_pre",
)

plan_forms, removed_plan_ids = render_plan_section(
    plan_entries=defaults["plans"],
    visible="plan" in visible,
    expanded=(selected_stage == "plan"),
    state_key=f"{state_key}_plan",
)

# --- Execution секция (inline, без entity_table) ---
if "execution" in visible:
    with st.expander("Execution", expanded=(selected_stage == "execution")):
        if st.button(
            "Create trade",
            width=200,
            key=f"{state_key}_create_trade",
        ):
            st.session_state[f"{TM_DEFAULT_PREFIX}analysis"] = analysis_id
            st.session_state[f"{TM_DEFAULT_PREFIX}asset"] = analysis.get("asset")
            st.switch_page("pages/trade_editor.py")

        trade_rows = list_trades(user_id, {"analysis_id": analysis_id})
        if trade_rows:
            df_exec = pd.DataFrame(trade_rows)
            df_exec["_link"] = "/trade_editor?id=" + \
                df_exec["id"].astype(str)
            display_cols = ["_link", "date_local", "session", "asset", "state", "net_pnl", "risk_reward"]
            for col in display_cols:
                if col not in df_exec.columns:
                    df_exec[col] = None
            st.dataframe(
                df_exec[display_cols],
                column_config={
                    "date_local": st.column_config.TextColumn("Date"),
                    "session": st.column_config.TextColumn("Session"),
                    "asset": st.column_config.TextColumn("Asset"),
                    "state": st.column_config.TextColumn("State"),
                    "net_pnl": st.column_config.NumberColumn("PnL"),
                    "risk_reward": st.column_config.NumberColumn("R:R"),
                    "_link": st.column_config.LinkColumn("Open", display_text="Open"),
                },
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No trades for this analysis.")

post_analysis_values, post_values = render_post_stage(
    stage_data=defaults["stages"].get("post-market"),
    defaults=defaults["analysis"],
    visible="post-market" in visible,
    expanded=(selected_stage == "post-market"),
    state_key=f"{state_key}_post",
)

# --- Нижняя панель actions ---
btn_back, btn_save, btn_delete, _ = st.columns([0.1, 0.1, 0.12, 0.68])
if btn_back.button("← Analysis", width="stretch"):
    st.switch_page("pages/analysis.py")
submitted = btn_save.button("Save", type="primary", width="stretch")
if not is_new_analysis:
    if btn_delete.button("Delete", type="secondary", width="stretch"):
        st.session_state["_ae_pending_delete"] = analysis_id
        st.rerun()

# --- Сохранение ---
if submitted:
    if pre_analysis_values and not pre_analysis_values.get("asset"):
        message_placeholder.error("Select an asset.")
        st.stop()
    if pre_analysis_values and not pre_analysis_values.get("daily_bias"):
        message_placeholder.error("Select a daily bias.")
        st.stop()
    if post_analysis_values and not post_analysis_values.get("fact_bias"):
        message_placeholder.error("Select a fact bias.")
        st.stop()
    if post_analysis_values and not post_analysis_values.get("day_result"):
        message_placeholder.error("Select a day result.")
        st.stop()

    analysis_payload: Dict[str, Any] = {"state": selected_stage}
    if pre_analysis_values:
        analysis_payload.update(pre_analysis_values)
    if post_analysis_values:
        analysis_payload.update(post_analysis_values)

    current_analysis_id = analysis_id
    try:
        with st.spinner("Saving..."):
            with transaction() as conn:
                if is_new_analysis:
                    current_analysis_id = add_analysis(
                        user_id, analysis_payload, conn=conn)
                else:
                    update_analysis(current_analysis_id, user_id,
                                    analysis_payload, conn=conn)

                if pre_values:
                    pre_stage_id = pre_values["stage_id"]
                    pre_values.update(
                        {
                            "analysis_id": current_analysis_id,
                            "type": "pre-market",
                        }
                    )
                    if pre_stage_id:
                        update_analysis_stage(
                            pre_stage_id, pre_values, conn=conn)
                    else:
                        pre_stage_id = add_analysis_stage(
                            pre_values, conn=conn)

                    persist_chart_editor(
                        attached_charts=pre_values["charts"]["rows_source"],
                        editor_rows=pre_values["charts"]["editor_value"],
                        conn=conn,
                        attach_chart=lambda chart_id, sid=pre_stage_id: attach_chart_to_analysis_stage(
                            sid, chart_id, conn=conn
                        ),
                    )

                if removed_plan_ids:
                    for stage_id in removed_plan_ids:
                        if not stage_id:
                            continue
                        delete_analysis_stage(stage_id, conn=conn)

                for plan_form in plan_forms:
                    charts_payload = plan_form.get("charts") or {}
                    plan_stage_id = plan_form.get("stage_id")
                    plan_payload = {
                        "analysis_id": current_analysis_id,
                        "type": "plan",
                        "summary": plan_form.get("summary") or "",
                    }
                    if plan_stage_id:
                        update_analysis_stage(
                            plan_stage_id, plan_payload, conn=conn)
                    else:
                        plan_payload["time_local"] = (
                            plan_form.get("time_local") or datetime.now()
                        )
                        plan_stage_id = add_analysis_stage(
                            plan_payload, conn=conn)

                    persist_chart_editor(
                        attached_charts=charts_payload.get(
                            "rows_source") or [],
                        editor_rows=charts_payload.get("editor_value") or [],
                        conn=conn,
                        attach_chart=lambda chart_id, sid=plan_stage_id: attach_chart_to_analysis_stage(
                            sid, chart_id, conn=conn
                        ),
                    )

                if post_values:
                    post_stage_id = post_values["stage_id"]
                    post_values.update(
                        {
                            "analysis_id": current_analysis_id,
                            "type": "post-market",
                        }
                    )
                    if post_stage_id:
                        update_analysis_stage(
                            post_stage_id, post_values, conn=conn)
                    else:
                        post_values.update({"time_local": datetime.now()})
                        post_stage_id = add_analysis_stage(
                            post_values, conn=conn)

                    persist_chart_editor(
                        attached_charts=post_values["charts"]["rows_source"],
                        editor_rows=post_values["charts"]["editor_value"],
                        conn=conn,
                        attach_chart=lambda chart_id, sid=post_stage_id: attach_chart_to_analysis_stage(
                            sid, chart_id, conn=conn
                        ),
                    )
                    base_note_ids = {
                        note.get("id")
                        for note in (post_values["notes"]["base_notes"] or [])
                        if note.get("id") is not None
                    }
                    staged_note_ids = {
                        int(nid) for nid in (post_values["notes"]["staged_note_ids"] or []) if nid is not None
                    }
                    for note_id in base_note_ids - staged_note_ids:
                        detach_note_from_analysis_stage(
                            post_stage_id, note_id, conn=conn)
                    for note_id in staged_note_ids - base_note_ids:
                        attach_note_to_analysis_stage(
                            post_stage_id, note_id, conn=conn)

        st.cache_data.clear()
        st.toast(
            "Analysis saved." if not is_new_analysis else "Analysis created.", icon="🔥")
        if is_new_analysis:
            st.query_params["id"] = str(current_analysis_id)
        st.rerun()
    except Exception as exc:
        message_placeholder.error(f"Failed to save analysis: {exc}")

# --- Диалог заметок (одиночный уровень — допустимо на странице) ---
render_note_manager()
