from datetime import date, time
from typing import Dict, List, Optional, Tuple

import streamlit as st

from config import (
    ASSETS,
    RESULT_VALUES,
    STATE_VALUES,
    EMOTIONAL_PROBLEMS
)
from db import (
    add_chart,
    cancel_trade,
    close_trade,
    link_chart_to_trade,
    list_accounts,
    list_setups,
    list_analysis,
    mark_missed,
    mark_reviewed,
    open_trade,
)
from helpers import apply_page_config_from_file


def string_to_float(raw: str, label: str) -> Optional[float]:
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{label}: ожидается число") from exc


def get_analysis_for_select() -> Dict[str, Optional[int]]:
    analyses = list_analysis()
    options: Dict[str, Optional[int]] = {"— Не выбрано —": None}
    for analysis in analyses:
        date_label = analysis.get("date_local") or "Без даты"
        asset_label = analysis.get("asset") or "—"
        label = f"{date_label} · {asset_label} (#{analysis['id']})"
        options[label] = analysis["id"]
    return options


def get_accounts_for_select() -> Dict[str, Optional[int]]:
    accounts = list_accounts()
    options: Dict[str, Optional[int]] = {}
    for acc in accounts:
        options[f"{acc['name']} (#{acc['id']})"] = acc["id"]
    return options


def get_setups_for_select() -> Dict[str, Optional[int]]:
    setups = list_setups()
    options: Dict[str, Optional[int]] = {}
    for setup in setups:
        options[f"{setup['name']} (#{setup['id']})"] = setup["id"]
    return options


def _parse_chart_lines(raw: str) -> List[Tuple[Optional[str], str]]:
    charts: List[Tuple[Optional[str], str]] = []
    for line in raw.splitlines():
        text = line.strip()
        if not text:
            continue
        if "|" in text:
            title_part, url_part = text.split("|", 1)
            title = title_part.strip() or None
            url = url_part.strip()
        else:
            title = None
            url = text
        if not url:
            continue
        charts.append((title, url))
    return charts


apply_page_config_from_file(__file__)

steps = {
    1: "Trade details",
    2: "Trade outcome",
    4: "Review",
}

with st.form("add_trade_form", clear_on_submit=False, border=False):
    # state_choice = st.selectbox(
    #     "State",
    #     STATE_VALUES,
    #     index=STATE_VALUES.index("open") if "open" in STATE_VALUES else 0,
    #     width=200
    # )

    analysis_options = get_analysis_for_select()
    account_options = get_accounts_for_select()
    setup_options = get_setups_for_select()

    options_col, charts_col = st.columns([1, 2])

    # Левая колонка: опции сделки
    options_con = options_col.container(border=True)
    c1, c2 = options_con.columns(2)
    trade_date = c1.date_input(
        "Date",
        value=date.today(),
        format="DD.MM.YYYY"
    )
    open_time = c2.time_input(
        "Time",
        value='now'
    )

    account_choice = options_con.selectbox(
        "Account",
        list(account_options.keys()),
        index=None,
    )

    asset_select = options_con.selectbox(
        "Asset",
        ASSETS,
        index=0,
    )
    analysis_labels = list(analysis_options.keys())
    analysis_choice = options_con.selectbox(
        "Analysis",
        analysis_labels,
        index=0,
    )
    setup_choice = options_con.selectbox(
        "Setup",
        list(setup_options.keys()),
        index=None,
    )

    net_pnl = options_con.number_input(
        "Net PnL, $",
        format="%1u",
        step=1,
    )

    risk_pct = options_con.slider(
        "Risk %",
        min_value=0.5,
        max_value=2.0,
        value=1.0,
        step=0.1,
    )

    risk_reward = options_con.number_input(
        "RR",
        format="%0.1f",
        step=0.1,
    )

    reward_percent = options_con.number_input(
        "Reward Percent %",
        format="%0.1f",
        step=0.1,
    )

    trade_result = options_con.segmented_control(
        "Result",
        options=[":green[Profit]", ":red[Loss]", ":blue[BE]"],
        default=":green[Profit]",
        selection_mode="single",
    )

    estimation_feedback = options_con.feedback("thumbs")

    observations = options_con.text_area(
        "Observations",
        height=80,
        placeholder="Ваши заметки по сделке",
    )

    emotional_problems = options_con.multiselect(
        "Emotional problems",
        EMOTIONAL_PROBLEMS,
        default=[],
        help="Можно выбрать несколько вариантов, если сделка сопровождалась несколькими эмоциональными трудностями.",
    )
    hot_thoughts = options_con.text_area(
        "Горячие мысли",
        height=80,
        placeholder="Мгновенные мысли по ходу сделки",
    )
    cold_thoughts = options_con.text_area(
        "Холодные мысли",
        height=80,
        placeholder="Рассудочные выводы и заметки",
    )

    # Правая колонка: чарты

    charts_col.markdown("### Чарты TradingView")
    charts_raw = charts_col.text_area(
        "Ссылки на чарты (по одной в строке, опционально: `Название | URL`)",
        placeholder="Breakout | https://www.tradingview.com/x/...",
        height=120,
    )

    state_note = ""
    result_choice = None
    net_pnl_raw = ""
    rr_raw = ""
    reward_pct_raw = ""
    retrospective_note = ""

    if state_choice in ("closed", "reviewed"):
        st.markdown("### Итоги сделки")
        c12, c13 = st.columns(2)
        result_choice = c12.selectbox(
            "Результат", ["— Выбрать —"] + RESULT_VALUES)
        net_pnl_raw = c12.text_input(
            "Net PnL", value="", placeholder="Обязательное поле")
        rr_raw = c13.text_input("Risk-Reward", value="",
                                placeholder="Обязательное поле")
        reward_pct_raw = c13.text_input(
            "Reward %", value="", placeholder="Опционально")
        retrospective_note = st.text_area(
            "Ретроспективная заметка",
            height=80,
            placeholder="Добавьте идеи после закрытия сделки",
        )
    elif state_choice in ("cancelled", "missed"):
        state_note = st.text_area(
            "Комментарий к состоянию",
            height=80,
            placeholder="Причина отмены или пропуска сделки",
        )

    submitted = st.form_submit_button("💾 Сохранить сделку", type="primary")

    if submitted:
        errors = []
        if not asset_select:
            errors.append("Укажите инструмент (тикер).")
        if state_choice in ("closed", "reviewed"):
            if not result_choice or result_choice == "— Выбрать —":
                errors.append(
                    "Для закрытой сделки необходимо выбрать результат.")
            if not net_pnl_raw:
                errors.append("Net PnL обязателен для закрытой сделки.")
            if not rr_raw:
                errors.append("Risk-Reward обязателен для закрытой сделки.")
        if errors:
            for err in errors:
                st.error(err)
            st.stop()

        try:
            net_pnl = (
                string_to_float(net_pnl_raw, "Net PnL")
                if state_choice in ("closed", "reviewed")
                else None
            )
            risk_reward = (
                string_to_float(rr_raw, "Risk-Reward")
                if state_choice in ("closed", "reviewed")
                else None
            )
            reward_percent = string_to_float(
                reward_pct_raw, "Reward %") if reward_pct_raw else None
        except ValueError as exc:
            st.error(str(exc))
            st.stop()

        base_payload = {
            "local_tz": local_tz.strip() or None,
            "date_local": trade_date.isoformat(),
            "time_local": open_time.strftime("%H:%M:%S"),
            "account_id": account_options[account_choice],
            "setup_id": setup_options[setup_choice],
            "analysis_id": analysis_options.get(analysis_choice),
            "asset": asset_value,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "position_size": position_size,
            "risk_pct": float(risk_pct),
            "session": session,
            "status": None if status_choice == "— Не задано —" else status_choice,
            "emotional_problems": emotional_problems,
            "hot_thoughts": hot_thoughts.strip() or None,
            "cold_thoughts": cold_thoughts.strip() or None,
            "retrospective_note": retrospective_note.strip() or None,
        }

        try:
            trade_id = open_trade(base_payload)
        except Exception as exc:
            st.error(f"Не удалось сохранить сделку: {exc}")
            st.stop()

        try:
            if state_choice == "closed":
                close_trade(
                    trade_id,
                    {
                        "result": result_choice,
                        "net_pnl": net_pnl,
                        "risk_reward": risk_reward,
                        "reward_percent": reward_percent,
                    },
                )
            elif state_choice == "reviewed":
                close_trade(
                    trade_id,
                    {
                        "result": result_choice,
                        "net_pnl": net_pnl,
                        "risk_reward": risk_reward,
                        "reward_percent": reward_percent,
                    },
                )
                mark_reviewed(trade_id, retrospective_note.strip() or None)
            elif state_choice == "cancelled":
                cancel_trade(trade_id, state_note.strip() or None)
            elif state_choice == "missed":
                mark_missed(trade_id, state_note.strip() or None)
        except Exception as exc:
            st.warning(
                f"Сделка создана с id={trade_id}, "
                f"но не получилось обновить состояние '{state_choice}': {exc}"
            )

        charts_to_store = _parse_chart_lines(charts_raw)
        for chart_title, chart_url in charts_to_store:
            try:
                chart_id = add_chart(title=chart_title, chart_url=chart_url)
                link_chart_to_trade(trade_id, chart_id)
            except Exception as exc:
                st.warning(f"Не удалось сохранить чарт '{chart_url}': {exc}")

        st.success(f"Готово! Сделка #{trade_id} сохранена.")
        st.session_state["selected_trade_id"] = trade_id
        st.session_state["selected_trade_state"] = state_choice
