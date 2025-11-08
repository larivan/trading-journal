from datetime import date, datetime, time
from typing import Any, Dict, List, Optional

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

RESULT_PLACEHOLDER = "— Не задано —"


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
    if not notes:
        return pd.DataFrame(columns=base_columns)
    df = pd.DataFrame(notes)
    for column in base_columns:
        if column not in df.columns:
            df[column] = ""
    return df[base_columns]


def _charts_dataframe(charts: List[Dict[str, Any]]) -> pd.DataFrame:
    base_columns = ["title", "chart_url", "description"]
    if not charts:
        return pd.DataFrame(columns=base_columns)
    df = pd.DataFrame(charts)
    for column in base_columns:
        if column not in df.columns:
            df[column] = ""
    return df[base_columns]


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
        placeholder="— Счёт не выбран —",
        formatter=lambda acc: f"{acc['name']} (#{acc['id']})",
    )
    setups = _option_with_placeholder(
        list_setups(),
        placeholder="— Сетап не выбран —",
        formatter=lambda setup: f"{setup['name']} (#{setup['id']})",
    )
    analyses = _option_with_placeholder(
        list_analysis(),
        placeholder="— Анализ не привязан —",
        formatter=lambda analysis: f"{analysis.get('date_local') or 'Без даты'} · "
        f"{analysis.get('asset') or '—'} (#{analysis['id']})",
    )
    account_labels = list(accounts.keys())
    setup_labels = list(setups.keys())
    analysis_labels = list(analyses.keys())

    observations_df = _notes_dataframe(
        list_notes_for_trade(trade_id))
    charts_df = _charts_dataframe(list_charts_for_trade(trade_id))
    observations_editor = observations_df
    charts_editor = charts_df

    current_state = trade.get("state") or "open"
    allowed_states = _allowed_statuses(current_state)
    selected_state = st.selectbox(
        "Статус сделки",
        allowed_states,
        index=allowed_states.index(current_state)
        if current_state in allowed_states else 0,
        help="Статусы двигаются последовательно, как в Jira.",
        width=200
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

    with st.form(f"trade_manager_form_{trade_id}"):
        col1, col2 = st.columns([1, 2])
        with col1:
            # --- Open stage ---
            if "open" in visible_stages:
                with st.expander(
                    "Данные при открытии",
                    expanded=(expanded_stage == "open"),
                ):
                    oc1, oc2 = st.columns(2)
                    date_value = oc1.date_input(
                        "Дата",
                        value=date_value,
                        format="DD.MM.YYYY",
                        key=f"tm_date_{trade_id}",
                    )
                    time_value = oc2.time_input(
                        "Время",
                        value=time_value,
                        key=f"tm_time_{trade_id}",
                    )

                    account_label = st.selectbox(
                        "Счёт",
                        account_labels,
                        index=account_labels.index(account_label),
                        key=f"tm_account_{trade_id}",
                    )

                    asset_default = st.selectbox(
                        "Инструмент",
                        assets,
                        index=assets.index(asset_default),
                        key=f"tm_asset_{trade_id}",
                    )

                    analysis_label = st.selectbox(
                        "Анализ дня",
                        analysis_labels,
                        index=analysis_labels.index(analysis_label),
                        key=f"tm_analysis_{trade_id}",
                    )

                    setup_label = st.selectbox(
                        "Сетап",
                        setup_labels,
                        index=setup_labels.index(setup_label),
                        key=f"tm_setup_{trade_id}",
                    )

                    risk_pct = st.slider(
                        "Риск на сделку, %",
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
                    "После закрытия",
                    expanded=(expanded_stage == "closed"),
                ):
                    cc1, cc2 = st.columns(2)
                    result_options = [RESULT_PLACEHOLDER] + RESULT_VALUES
                    result_value = cc1.selectbox(
                        "Результат",
                        result_options,
                        index=result_options.index(closed_defaults["result"])
                        if closed_defaults["result"] in result_options else 0,
                        key=f"tm_result_{trade_id}",
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
                        "Горячие мысли",
                        height=100,
                        value=closed_defaults["hot_thoughts"],
                        key=f"tm_hot_{trade_id}",
                    )
                    emotional_defaults = st.multiselect(
                        "Эмоциональные сложности",
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
                    "Ревью сделки",
                    expanded=(expanded_stage == "review"),
                ):
                    cold_thoughts_value = st.text_area(
                        "Холодные мысли",
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
            st.markdown("#### Чарты")
            preview_container = st.container()
            for chart in charts_editor.to_dict("records"):
                url = (chart.get("chart_url") or "").strip()
                if not url:
                    continue
                with preview_container:
                    caption = chart.get("title") or url
                    st.image(url, caption=caption, use_container_width=True)

            st.caption(
                "Добавьте ссылки на скриншоты графиков. Новые строки добавляются кнопкой «+».")
            charts_editor = st.data_editor(
                charts_df,
                hide_index=True,
                key=f"tm_charts_{trade_id}",
                num_rows="dynamic",
                column_config={
                    "title": st.column_config.TextColumn("Название"),
                    "chart_url": st.column_config.TextColumn(
                        "Ссылка", help="TradingView / телеграм и т.д."),
                    "description": st.column_config.TextColumn(
                        "Комментарий", help="Опционально"),
                },
            )

            st.markdown("#### Заметки по сделке, наблюдения")
            st.caption(
                "Observations — краткие заметки по сделке, можно добавлять несколько записей.")
            observations_editor = st.data_editor(
                observations_df,
                hide_index=True,
                key=f"tm_observations_{trade_id}",
                num_rows="dynamic",
                column_config={
                    "id": st.column_config.NumberColumn(
                        "ID", disabled=True, width="small"),
                    "title": st.column_config.TextColumn("Заголовок"),
                    "body": st.column_config.TextColumn(
                        "Текст заметки", width="medium"),
                    "tags": st.column_config.TextColumn(
                        "Теги", help="Опциональные маркеры для фильтрации"),
                },
            )

        submitted = st.form_submit_button(
            "Сохранить изменения",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    errors: List[str] = []
    if selected_state in ("closed", "reviewed"):
        if not closed_inputs:
            errors.append("Заполните данные блока «После закрытия».")
        else:
            if closed_inputs["result"] == RESULT_PLACEHOLDER:
                errors.append("Выберите результат сделки.")
            if closed_inputs["net_pnl"] is None:
                errors.append("Укажите Net PnL.")
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
            observations_editor.to_dict("records")
        )
        replace_trade_charts(
            trade_id,
            charts_editor.to_dict("records"),
        )
        st.success("Сделка обновлена.")
        st.rerun()
    except Exception as exc:  # pragma: no cover - UI feedback
        st.error(f"Не удалось обновить сделку: {exc}")
