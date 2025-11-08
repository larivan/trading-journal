import streamlit as st

from components.trade_detail import trade_detail_fragment
from db import get_trade_by_id
from helpers import apply_page_config_from_file


apply_page_config_from_file(__file__)

qp = st.query_params
trade_id_param = qp.get("trade_id")
if trade_id_param is None:
    trade_id_param = st.session_state.get("trade_detail_id")
else:
    st.session_state["trade_detail_id"] = trade_id_param

if trade_id_param is None:
    st.error("Не указан trade_id.")
    st.stop()

try:
    trade_id = int(trade_id_param)
except ValueError:
    st.error("trade_id должен быть числом.")
    st.stop()

st.session_state["trade_detail_id"] = trade_id

trade = get_trade_by_id(trade_id)
if not trade:
    st.error(f"Сделка #{trade_id} не найдена.")
    st.stop()

trade_detail_fragment(trade)
