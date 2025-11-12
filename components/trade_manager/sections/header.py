"""Заголовок трейд-менеджера с действиями."""

from typing import Optional

import streamlit as st


def render_header_actions(trade_key: str, trade_id: Optional[int] = None) -> bool:
    """Кнопки действия в заголовке: открыть сделку и сохранить изменения."""
    col_save, col_open = st.columns(2, gap="small")
    submitted = col_save.button(
        "Save changes",
        type="primary",
        key=f"tm_submit_{trade_key}",
        use_container_width=True,
    )
    trade_url = f"/trade?id={trade_id}" if trade_id is not None else None
    col_open.link_button(
        "Open in new tab",
        url=trade_url or "#",
        disabled=trade_url is None,
        use_container_width=True,
    )
    return submitted
