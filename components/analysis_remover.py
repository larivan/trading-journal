from typing import Callable, Optional

import streamlit as st

from db import delete_analysis


def render_analysis_remove_dialog(
    *,
    analysis_id: Optional[int],
    on_deleted: Optional[Callable[[], None]] = None,
    on_cancel: Optional[Callable[[], None]] = None,
) -> None:
    @st.dialog("Удаление анализа")
    def _dialog() -> None:
        if not analysis_id:
            st.info("Анализ не выбран.")
            return

        st.warning(
            "Анализ будет удалён безвозвратно. Подтвердите действие.",
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
                delete_analysis(analysis_id)
                st.success("Анализ удалён.")
                if on_deleted:
                    on_deleted()
            except Exception as exc:  # pragma: no cover
                st.error(f"Не удалось удалить анализ: {exc}")
        if cancel and on_cancel:
            on_cancel()

    _dialog()
