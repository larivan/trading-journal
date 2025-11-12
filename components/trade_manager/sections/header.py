"""Заголовок трейд-менеджера с действиями."""

from typing import Callable, Optional

import streamlit as st


def render_header_actions(
    trade_key: str,
    *,
    trade_id: Optional[int] = None,
    on_cancel: Optional[Callable[[], None]] = None,
) -> bool:
    """Кнопки действия в заголовке: открыть сделку, сохранить или отменить изменения."""
    if on_cancel:
        col_save, col_open, col_cancel = st.columns([2, 1, 1], gap="small")
    else:
        col_save, col_open = st.columns([2, 1], gap="small")
        col_cancel = None
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
    if col_cancel is not None:
        cancel_clicked = col_cancel.button(
            "Cancel",
            key=f"tm_cancel_{trade_key}",
            use_container_width=True,
        )
        if cancel_clicked and on_cancel:
            on_cancel()
    return submitted
