from datetime import date, datetime, time
from typing import Any, Dict, Optional

import streamlit as st

from config import ASSETS, RESULT_VALUES, SESSION_VALUES, STATE_VALUES


def _parse_time(value: Optional[str]) -> time:
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


def _parse_date(value: Optional[str]) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return date.today()


def _format_decimal(value: Optional[Any]) -> str:
    if value is None or value == "":
        return ""
    try:
        return str(float(value))
    except (TypeError, ValueError):
        return ""


def render_trade_form(
    account_options: Dict[str, Optional[int]],
    *,
    initial: Optional[Dict[str, Any]] = None,
    form_key: str,
    submit_label: str,
) -> Optional[Dict[str, Any]]:
    """
    Render trade form and return normalized payload after submit.
    """
    initial = initial or {}
    trade_date = _parse_date(initial.get("date_local"))
    trade_time = _parse_time(initial.get("time_local"))

    account_choices = ["Не выбран"] + [
        label for label, value in account_options.items() if value is not None
    ]
    account_lookup = {"Не выбран": None}
    account_lookup.update({
        label: value for label, value in account_options.items() if value is not None
    })
    current_account_id = initial.get("account_id")
    account_default_label = next(
        (label for label, value in account_lookup.items()
         if value == current_account_id),
        "Не выбран",
    )

    asset_default = initial.get("asset") or (ASSETS[0] if ASSETS else "")
    state_default = initial.get("state") or (STATE_VALUES[0] if STATE_VALUES else "")
    result_default = initial.get("result")
    session_default = initial.get("session")

    pnl_default = _format_decimal(initial.get("net_pnl"))
    rr_default = _format_decimal(initial.get("risk_reward"))

    with st.form(form_key):
        fc1, fc2 = st.columns(2)
        date_value = fc1.date_input(
            "Дата",
            value=trade_date,
            key=f"{form_key}_date",
            format="DD.MM.YYYY",
        )
        time_value = fc2.time_input(
            "Время",
            value=trade_time,
            key=f"{form_key}_time",
        )

        fc3, fc4 = st.columns(2)
        account_value = fc3.selectbox(
            "Счёт",
            account_choices,
            index=account_choices.index(account_default_label),
            key=f"{form_key}_account",
        )
        asset_value = fc4.selectbox(
            "Инструмент",
            ASSETS or [asset_default],
            index=(ASSETS.index(asset_default)
                   if asset_default in ASSETS and ASSETS else 0),
            key=f"{form_key}_asset",
        )

        fc5, fc6 = st.columns(2)
        state_value = fc5.selectbox(
            "Состояние",
            STATE_VALUES or ["open"],
            index=(STATE_VALUES.index(state_default)
                   if state_default in STATE_VALUES and STATE_VALUES else 0),
            key=f"{form_key}_state",
        )
        session_options = ["Не задано"] + (SESSION_VALUES or [])
        session_value = fc6.selectbox(
            "Сессия",
            session_options,
            index=(session_options.index(session_default)
                   if session_default in session_options else 0),
            key=f"{form_key}_session",
        )

        fc7, fc8 = st.columns(2)
        result_options = ["Не задано"] + (RESULT_VALUES or [])
        result_value = fc7.selectbox(
            "Результат",
            result_options,
            index=(result_options.index(result_default)
                   if result_default in result_options else 0),
            key=f"{form_key}_result",
        )
        pnl_value = fc8.text_input(
            "PnL",
            value=pnl_default,
            key=f"{form_key}_pnl",
            placeholder="Например 125.5",
        )

        rr_value = st.text_input(
            "R:R",
            value=rr_default,
            key=f"{form_key}_rr",
            placeholder="Например 2.5",
        )

        submitted = st.form_submit_button(submit_label, use_container_width=True)

    if not submitted:
        return None

    def _parse_float(raw: str) -> Optional[float]:
        raw = (raw or "").strip().replace(",", ".")
        if not raw:
            return None
        try:
            return float(raw)
        except ValueError:
            st.error("Поля PnL и R:R должны быть числами.")
            return None

    pnl_float = _parse_float(pnl_value)
    rr_float = _parse_float(rr_value)
    if (pnl_value and pnl_float is None) or (rr_value and rr_float is None):
        return None

    payload: Dict[str, Any] = {
        "date_local": date_value.isoformat(),
        "time_local": time_value.strftime("%H:%M:%S"),
        "account_id": account_lookup.get(account_value),
        "asset": asset_value,
        "state": state_value,
        "session": None if session_value == "Не задано" else session_value,
        "result": None if result_value == "Не задано" else result_value,
        "net_pnl": pnl_float,
        "risk_reward": rr_float,
    }
    return payload
