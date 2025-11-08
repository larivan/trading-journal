# pages/edit.py
import streamlit as st
import pandas as pd
from db import list_trades  # или get_trade_by_id, если добавишь

qp = st.query_params
tid = qp.get("trade_id")
if not tid:
    st.error("Не указан trade_id")
    st.stop()

tid = int(tid)
rows = list_trades({})
row = next((r for r in rows if r["id"] == tid), None)
if not row:
    st.error(f"Сделка #{tid} не найдена")
    st.stop()

st.title(f"✏️ Редактирование сделки #{tid}")
# Тут форма редактирования по твоей модели (pnl / rr / notes / и т.д.)
