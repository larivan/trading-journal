"""Компонент удаления сделки с подтверждающей модалкой."""

from typing import Callable, Optional

import streamlit as st

from db import delete_trade


def render_trade_remove_dialog(
    *,
    trade_id: Optional[int],
    on_deleted: Optional[Callable[[], None]] = None,
    on_cancel: Optional[Callable[[], None]] = None,
) -> None:
    """Показывает модалку удаления выбранной сделки."""

    @st.dialog("Удаление сделки")
    def _dialog() -> None:
        if not trade_id:
            st.info("Сделка не выбрана.")
            return
        st.warning(
            "Сделка будет удалена безвозвратно. Подтвердите действие.",
            icon="⚠️",
        )
        col_ok, col_cancel = st.columns(2)
        confirm = col_ok.button(
            "Удалить",
            type="primary",
            use_container_width=True,
        )
        cancel = col_cancel.button(
            "Отмена",
            use_container_width=True,
        )
        if confirm:
            try:
                delete_trade(trade_id)
                st.success("Сделка удалена.")
                if on_deleted:
                    on_deleted()
                st.rerun()
            except Exception as exc:  # pragma: no cover
                st.error(f"Не удалось удалить сделку: {exc}")
        if cancel and on_cancel:
            on_cancel()

    _dialog()
