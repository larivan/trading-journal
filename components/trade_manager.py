from datetime import date, datetime, time
from typing import Any, Dict, List, Optional, Set

import pandas as pd
import streamlit as st

from config import ASSETS, EMOTIONAL_PROBLEMS, RESULT_VALUES
from db import (
    list_accounts,
    list_analysis,
    list_charts_for_trade,
    list_notes_for_trade,
    list_setups,
    parse_emotional_problems,
    replace_trade_charts,
    replace_trade_notes,
    update_trade,
)

STATUS_TRANSITIONS: Dict[str, List[str]] = {
    "open": ["open", "closed", "cancelled", "missed"],
    "closed": ["closed", "reviewed"],
    "reviewed": ["reviewed"],
    "cancelled": ["cancelled"],
    "missed": ["missed"],
}

STATUS_STAGE = {
    "open": "open",
    "closed": "closed",
    "reviewed": "review",
    "cancelled": "open",
    "missed": "open",
}

RESULT_PLACEHOLDER = "— Not set —"

STATE_LABELS = {
    "open": "Open",
    "closed": "Closed",
    "reviewed": "Reviewed",
    "cancelled": "Cancelled",
    "missed": "Missed",
}

RESULT_LABELS = {
    "win": "Win",
    "loss": "Loss",
    "be": "Break-even",
}


def _state_label(value: Optional[str]) -> str:
    if not value:
        return ""
    return STATE_LABELS.get(value, value.replace("_", " ").title())


def _result_label(value: Optional[str]) -> str:
    if not value:
        return ""
    return RESULT_LABELS.get(value, value.replace("_", " ").title())


def _parse_time_value(value: Optional[str]) -> time:
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                continue
    now = datetime.now().time()
    return time(hour=now.hour, minute=now.minute, second=0)


def _parse_date_value(value: Optional[str]) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return date.today()


def _option_with_placeholder(
    items: List[Dict[str, Any]],
    *,
    placeholder: str,
    formatter,
) -> Dict[str, Optional[int]]:
    options: Dict[str, Optional[int]] = {placeholder: None}
    for item in items:
        options[formatter(item)] = item["id"]
    return options


def _current_label(options: Dict[str, Optional[int]],
                   current_value: Optional[int]) -> str:
    for label, value in options.items():
        if value == current_value:
            return label
    return next(iter(options))


def _notes_dataframe(notes: List[Dict[str, Any]]) -> pd.DataFrame:
    base_columns = ["id", "title", "body", "tags"]
    df = pd.DataFrame(notes or [])
    if df.empty:
        df = pd.DataFrame([{
            "id": None,
            "title": "",
            "body": "",
            "tags": [],
        }])
    for column in base_columns:
        if column not in df.columns:
            df[column] = "" if column != "id" else None
    df = df[base_columns]
    df["tags"] = df["tags"].apply(_split_tags)
    return df


def _charts_dataframe(charts: List[Dict[str, Any]]) -> pd.DataFrame:
    base_columns = ["chart_url", "description"]
    df = pd.DataFrame(charts or [])
    if df.empty:
        return pd.DataFrame(columns=base_columns)
    if "chart_url" not in df.columns:
        df["chart_url"] = ""
    if "description" not in df.columns:
        df["description"] = ""
    if "title" in df.columns:
        mask = df["description"].isna() | (df["description"] == "")
        df.loc[mask, "description"] = df.loc[mask, "title"].fillna("")
    df["chart_url"] = df["chart_url"].fillna("")
    df["description"] = df["description"].fillna("")
    return df[base_columns]


def _split_tags(raw_value: Any) -> List[str]:
    if isinstance(raw_value, list):
        candidates = raw_value
    elif raw_value is None or pd.isna(raw_value):
        candidates = []
    else:
        candidates = str(raw_value).split(",")
    normalized: List[str] = []
    for tag in candidates:
        if tag is None:
            continue
        tag_value = str(tag).strip()
        if tag_value:
            normalized.append(tag_value)
    return normalized


def _serialize_tags(raw_value: Any) -> Optional[str]:
    if isinstance(raw_value, list):
        normalized: List[str] = []
        for tag in raw_value:
            if tag is None or pd.isna(tag):
                continue
            tag_value = str(tag).strip()
            if tag_value:
                normalized.append(tag_value)
        return ", ".join(normalized) or None
    if raw_value is None or pd.isna(raw_value):
        return None
    raw_text = str(raw_value).strip()
    return raw_text or None


def _prepare_note_records(editor_df: Optional[pd.DataFrame],
                          existing_ids: Optional[Set[int]] = None) -> List[Dict[str, Any]]:
    if editor_df is None:
        return []
    existing_ids = {
        int(note_id) for note_id in (existing_ids or set()) if note_id is not None
    }
    working_df = editor_df.copy()
    if "id" not in working_df.columns:
        index_label = working_df.index.name or "index"
        working_df = working_df.reset_index().rename(columns={index_label: "id"})
    normalized_ids: List[Optional[int]] = []
    for raw_id in working_df["id"].tolist():
        try:
            candidate = int(raw_id)
        except (TypeError, ValueError):
            candidate = None
        normalized_ids.append(candidate if candidate in existing_ids else None)
    working_df["id"] = normalized_ids
    records: List[Dict[str, Any]] = []
    for row in working_df.to_dict("records"):
        records.append({
            "id": row.get("id"),
            "title": (row.get("title") or "").strip() or None,
            "body": (row.get("body") or "").strip(),
            "tags": _serialize_tags(row.get("tags")),
        })
    return records


def _prepare_chart_records(editor_df: Optional[pd.DataFrame]) -> List[Dict[str, Any]]:
    if editor_df is None:
        return []
    records: List[Dict[str, Any]] = []
    for row in editor_df.to_dict("records"):
        chart_url = (row.get("chart_url") or "").strip()
        if not chart_url:
            continue
        description = (row.get("description") or "").strip()
        records.append({
            "title": description or None,
            "chart_url": chart_url,
            "description": description or None,
        })
    return records


def _allowed_statuses(current_state: str) -> List[str]:
    return STATUS_TRANSITIONS.get(current_state, ["open"])


def _visible_stages(selected_state: str) -> List[str]:
    stage = STATUS_STAGE.get(selected_state, "open")
    if stage == "open":
        return ["open"]
    if stage == "closed":
        return ["open", "closed"]
    if stage == "review":
        return ["open", "closed", "review"]
    return ["open"]


def render_trade_manager(trade: Dict[str, Any]) -> None:
    trade_id = trade["id"]
    accounts = _option_with_placeholder(
        list_accounts(),
        placeholder="— Account not selected —",
        formatter=lambda acc: f"{acc['name']} (#{acc['id']})",
    )
    setups = _option_with_placeholder(
        list_setups(),
        placeholder="— Setup not selected —",
        formatter=lambda setup: f"{setup['name']} (#{setup['id']})",
    )
    analyses = _option_with_placeholder(
        list_analysis(),
        placeholder="— Analysis not linked —",
        formatter=lambda analysis: f"{analysis.get('date_local') or 'No date'} · "
        f"{analysis.get('asset') or '—'} (#{analysis['id']})",
    )
    account_labels = list(accounts.keys())
    setup_labels = list(setups.keys())
    analysis_labels = list(analyses.keys())

    trade_notes = list_notes_for_trade(trade_id)
    observations_df = _notes_dataframe(trade_notes)
    existing_note_ids: Set[int] = {
        int(note["id"]) for note in trade_notes if note.get("id") is not None
    }
    tag_options = sorted({
        tag for tags in observations_df["tags"].tolist() for tag in tags
    })
    charts_df = _charts_dataframe(list_charts_for_trade(trade_id))
    observations_editor = observations_df.copy()
    charts_state_key = f"tm_charts_state_{trade_id}"
    if charts_state_key not in st.session_state:
        st.session_state[charts_state_key] = charts_df.copy()
    charts_editor = st.session_state[charts_state_key]

    current_state = trade.get("state") or "open"
    allowed_states = _allowed_statuses(current_state)
    selected_state = st.selectbox(
        "Trade status",
        allowed_states,
        index=allowed_states.index(current_state)
        if current_state in allowed_states else 0,
        help="Statuses move sequentially similar to Jira.",
        width=200,
        format_func=_state_label,
    )
    visible_stages = _visible_stages(selected_state)
    expanded_stage = STATUS_STAGE.get(selected_state, "open")

    date_value = _parse_date_value(trade.get("date_local"))
    time_value = _parse_time_value(trade.get("time_local"))
    account_label = _current_label(accounts, trade.get("account_id"))
    setup_label = _current_label(setups, trade.get("setup_id"))
    analysis_label = _current_label(analyses, trade.get("analysis_id"))

    assets = ASSETS or [trade.get("asset") or "—"]
    asset_default = trade.get("asset") if trade.get(
        "asset") in assets else assets[0]
    emotional_defaults = parse_emotional_problems(
        trade.get("emotional_problems"))

    closed_defaults = {
        "result": trade.get("result") or RESULT_PLACEHOLDER,
        "net_pnl": trade.get("net_pnl") or 0.0,
        "risk_reward": trade.get("risk_reward") or 0.0,
        "reward_percent": trade.get("reward_percent") or 0.0,
        "hot_thoughts": trade.get("hot_thoughts") or "",
    }
    review_defaults = {
        "cold_thoughts": trade.get("cold_thoughts") or "",
        "estimation": trade.get("estimation") or 0,
    }

    view_clicked = False
    with st.form(f"trade_manager_form_{trade_id}"):
        col1, col2 = st.columns([1, 2])
        with col1:
            # --- Open stage ---
            if "open" in visible_stages:
                with st.expander(
                    "Opening details",
                    expanded=(expanded_stage == "open"),
                ):
                    oc1, oc2 = st.columns(2)
                    date_value = oc1.date_input(
                        "Date",
                        value=date_value,
                        format="DD.MM.YYYY",
                        key=f"tm_date_{trade_id}",
                    )
                    time_value = oc2.time_input(
                        "Time",
                        value=time_value,
                        key=f"tm_time_{trade_id}",
                    )

                    account_label = st.selectbox(
                        "Account",
                        account_labels,
                        index=account_labels.index(account_label),
                        key=f"tm_account_{trade_id}",
                    )

                    asset_default = st.selectbox(
                        "Asset",
                        assets,
                        index=assets.index(asset_default),
                        key=f"tm_asset_{trade_id}",
                    )

                    analysis_label = st.selectbox(
                        "Daily analysis",
                        analysis_labels,
                        index=analysis_labels.index(analysis_label),
                        key=f"tm_analysis_{trade_id}",
                    )

                    setup_label = st.selectbox(
                        "Setup",
                        setup_labels,
                        index=setup_labels.index(setup_label),
                        key=f"tm_setup_{trade_id}",
                    )

                    risk_pct = st.slider(
                        "Risk per trade, %",
                        min_value=0.5,
                        max_value=2.0,
                        value=float(trade.get("risk_pct") or 1.0),
                        step=0.1,
                        key=f"tm_risk_{trade_id}",
                    )

            # --- Closed stage ---
            closed_inputs = {}
            if "closed" in visible_stages:
                with st.expander(
                    "After close",
                    expanded=(expanded_stage == "closed"),
                ):
                    cc1, cc2 = st.columns(2)
                    result_options = [RESULT_PLACEHOLDER] + RESULT_VALUES
                    result_value = cc1.selectbox(
                        "Result",
                        result_options,
                        index=result_options.index(closed_defaults["result"])
                        if closed_defaults["result"] in result_options else 0,
                        key=f"tm_result_{trade_id}",
                        format_func=lambda value: value if value == RESULT_PLACEHOLDER else _result_label(value),
                    )
                    net_pnl_value = cc2.number_input(
                        "Net PnL, $",
                        value=float(closed_defaults["net_pnl"]),
                        step=1.0,
                        key=f"tm_pnl_{trade_id}",
                    )
                    risk_reward_value = cc1.number_input(
                        "R:R",
                        value=float(closed_defaults["risk_reward"]),
                        step=0.1,
                        key=f"tm_rr_{trade_id}",
                    )
                    reward_percent_value = cc2.number_input(
                        "Reward %",
                        value=float(closed_defaults["reward_percent"]),
                        step=0.5,
                        key=f"tm_reward_{trade_id}",
                    )

                    hot_thoughts_value = st.text_area(
                        "Hot thoughts",
                        height=100,
                        value=closed_defaults["hot_thoughts"],
                        key=f"tm_hot_{trade_id}",
                    )
                    emotional_defaults = st.multiselect(
                        "Emotional challenges",
                        EMOTIONAL_PROBLEMS,
                        default=emotional_defaults,
                        key=f"tm_emotions_{trade_id}",
                    )
                    closed_inputs = {
                        "result": result_value,
                        "net_pnl": net_pnl_value,
                        "risk_reward": risk_reward_value,
                        "reward_percent": reward_percent_value,
                        "hot_thoughts": hot_thoughts_value,
                    }

            # --- Review stage ---
            review_inputs = None
            if "review" in visible_stages:
                with st.expander(
                    "Trade review",
                    expanded=(expanded_stage == "review"),
                ):
                    cold_thoughts_value = st.text_area(
                        "Cold thoughts",
                        height=120,
                        value=review_defaults["cold_thoughts"],
                        key=f"tm_cold_{trade_id}",
                    )
                    estimation_value = st.feedback(
                        "thumbs",
                        default=int(review_defaults["estimation"]),
                        key=f"tm_estimation_{trade_id}",
                    )
                    review_inputs = {
                        "cold_thoughts": cold_thoughts_value,
                        "estimation": estimation_value,
                    }

        with col2:
            st.markdown("#### Charts")
            st.caption(
                "Add a chart link (URL) and optional description. Preview is generated automatically.")
            charts_display_df = charts_editor.copy()
            charts_display_df["preview"] = charts_display_df["chart_url"]
            edited_charts = st.data_editor(
                charts_display_df,
                hide_index=True,
                key=f"tm_charts_{trade_id}",
                num_rows="dynamic",
                column_config={
                    "chart_url": st.column_config.TextColumn(
                        "Link", help="TradingView, Telegram, etc."),
                    "description": st.column_config.TextColumn(
                        "Description", help="Optional comment"),
                    "preview": st.column_config.ImageColumn(
                        "Preview",
                        help="Image fetched from the provided link.",
                        width="medium",
                    ),
                },
                column_order=["chart_url", "description", "preview"],
            )
            if edited_charts is not None:
                cleaned_charts = edited_charts.drop(
                    columns=["preview"], errors="ignore").copy()
            else:
                cleaned_charts = charts_editor.copy()
            st.session_state[charts_state_key] = cleaned_charts
            charts_editor = cleaned_charts

            st.markdown("#### Trade observations")
            st.caption(
                "Add short observations for the trade. You can keep multiple notes.")
            observations_editor = st.data_editor(
                observations_editor,
                hide_index=True,
                key=f"tm_observations_{trade_id}",
                num_rows="dynamic",
                column_config={
                    "id": st.column_config.NumberColumn(
                        "ID", disabled=True, width="small"),
                    "title": st.column_config.TextColumn("Title"),
                    "body": st.column_config.TextColumn(
                        "Note", width="medium"),
                    "tags": st.column_config.MultiselectColumn(
                        "Tags",
                        help="Optional markers for filtering",
                        options=tag_options,
                        accept_new_options=True,
                        default=[],
                    ),
                },
                column_order=["id", "title", "body", "tags"],
            )

        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            submitted = st.form_submit_button(
                "Save changes",
                type="primary",
            )
        with btn_col2:
            view_clicked = st.form_submit_button(
                "View",
                type="secondary",
            )

    if view_clicked:
        st.info("View mode will be available soon.")

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
        "date_local": date_value.isoformat(),
        "time_local": time_value.strftime("%H:%M:%S"),
        "account_id": accounts[account_label],
        "asset": asset_default,
        "analysis_id": analyses[analysis_label],
        "setup_id": setups[setup_label],
        "risk_pct": float(risk_pct),
        "state": selected_state,
    }

    if closed_inputs:
        payload.update({
            "result": None if closed_inputs["result"] == RESULT_PLACEHOLDER else closed_inputs["result"],
            "net_pnl": float(closed_inputs["net_pnl"]),
            "risk_reward": float(closed_inputs["risk_reward"]),
            "reward_percent": float(closed_inputs["reward_percent"]),
            "hot_thoughts": closed_inputs["hot_thoughts"].strip() or None,
            "emotional_problems": emotional_defaults,
        })
    else:
        payload.update({
            "result": None,
            "net_pnl": None,
            "risk_reward": None,
            "reward_percent": None,
            "hot_thoughts": None,
        })

    if review_inputs:
        payload.update({
            "cold_thoughts": review_inputs["cold_thoughts"].strip() or None,
            "estimation": int(review_inputs["estimation"]),
        })
    else:
        payload.update({
            "cold_thoughts": None if selected_state != "reviewed" else trade.get("cold_thoughts"),
            "estimation": None if selected_state != "reviewed" else trade.get("estimation"),
        })

    if selected_state in ("closed", "reviewed") and not trade.get("closed_at_utc"):
        payload["closed_at_utc"] = datetime.utcnow().strftime(
            "%Y-%m-%dT%H:%M:%S")

    try:
        update_trade(trade_id, payload)
        replace_trade_notes(
            trade_id,
            _prepare_note_records(observations_editor, existing_note_ids)
        )
        replace_trade_charts(
            trade_id,
            _prepare_chart_records(charts_editor),
        )
        st.session_state.pop(charts_state_key, None)
        st.success("Trade updated.")
        st.rerun()
    except Exception as exc:  # pragma: no cover - UI feedback
        st.error(f"Failed to update the trade: {exc}")
