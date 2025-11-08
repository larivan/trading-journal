from typing import Dict, Optional, Any

import streamlit as st


def _fmt_value(value: Optional[Any], placeholder: str = "—") -> str:
    if value is None or value == "":
        return placeholder
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


@st.fragment
def trade_detail_fragment(trade: Dict[str, Any]) -> None:
    """Reusable block that renders core info for a trade."""
    st.subheader(f"Сделка #{trade.get('id')} • {trade.get('asset') or '—'}")

    meta_col1, meta_col2, meta_col3 = st.columns(3)
    meta_col1.metric("Дата", trade.get("date_local") or "—")
    meta_col2.metric("Время", trade.get("time_local") or "—")
    meta_col3.metric("Сессия", trade.get("session") or "—")

    info_col1, info_col2, info_col3 = st.columns(3)
    info_col1.metric("Состояние", trade.get("state") or "—")
    info_col2.metric("Результат", trade.get("result") or "—")
    info_col3.metric("PnL", _fmt_value(trade.get("net_pnl")))

    st.divider()

    price_col1, price_col2, price_col3, price_col4 = st.columns(4)
    price_col1.write(f"Entry: {_fmt_value(trade.get('entry_price'))}")
    price_col2.write(f"Stop: {_fmt_value(trade.get('stop_loss'))}")
    price_col3.write(f"Take: {_fmt_value(trade.get('take_profit'))}")
    price_col4.write(f"Risk %: {_fmt_value(trade.get('risk_pct'))}")

    st.divider()

    st.write("**Горячие мысли**")
    st.write(trade.get("hot_thoughts") or "_Пусто_")

    st.write("**Холодные мысли**")
    st.write(trade.get("cold_thoughts") or "_Пусто_")

    if trade.get("retrospective_note"):
        st.write("**Ретроспектива**")
        st.write(trade["retrospective_note"])
