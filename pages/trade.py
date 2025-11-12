from typing import Optional

import streamlit as st

from components.trade_manager import render_trade_manager
from db import get_trade_by_id
from helpers import apply_page_config_from_file


def _get_query_param_value(name: str) -> str:
    """Safely extract first value for a query param."""
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[-1] if value else ""
    return value or ""


def _parse_trade_id(raw: str) -> Optional[int]:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


apply_page_config_from_file(__file__)

st.session_state.setdefault("selected_trade_id", None)
previous_trade_id = st.session_state.get("trade_page_active_id")

raw_trade_id = _get_query_param_value(
    "trade_id") or _get_query_param_value("id")

if not raw_trade_id:
    if previous_trade_id is not None:
        st.session_state["trade_page_active_id"] = None
    st.error(
        "Страница открыта без параметра trade_id. Откройте сделку из трейд-менеджера.")
    st.stop()

trade_id = _parse_trade_id(raw_trade_id)
if trade_id is None:
    st.error("Некорректный параметр trade_id: укажите целое число.")
    st.stop()

trade = get_trade_by_id(trade_id)
if not trade:
    st.error(f"Сделка #{trade_id} не найдена.")
    st.stop()

st.session_state["trade_page_active_id"] = trade_id
st.session_state["selected_trade_id"] = trade_id

context_key = f"page_trade_{trade_id}"
render_trade_manager(
    trade,
    context=context_key
)
