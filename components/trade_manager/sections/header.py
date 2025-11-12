"""Заголовок трейд-менеджера с действиями."""

from typing import Callable, Optional

import streamlit as st


def render_header_actions(
    trade_key: str,
    *,
    on_cancel: Optional[Callable[[], None]] = None,
) -> bool:
    """Кнопки действия в заголовке: сохранить или отменить изменения."""
    if on_cancel:
        col_save, col_cancel = st.columns(2, gap="small")
    else:
        col_save = st.columns(1)[0]
        col_cancel = None
    submitted = col_save.button(
        "Save changes",
        type="primary",
        key=f"tm_submit_{trade_key}",
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
