from typing import Callable, Optional

import streamlit as st

from .analysis_form import (
    build_analysis_form_defaults,
    render_analysis_form,
    serialize_analysis_values,
)
from db import get_analysis, update_analysis


def render_analysis_manager_dialog(
    *,
    analysis_id: Optional[int],
    on_saved: Optional[Callable[[], None]] = None,
    on_close: Optional[Callable[[], None]] = None,
) -> None:
    @st.dialog("Редактирование анализа")
    def _dialog() -> None:
        if not analysis_id:
            st.info("Анализ не выбран.")
            return
        analysis = get_analysis(analysis_id)
        if not analysis:
            st.error("Анализ не найден или уже удалён.")
            close = st.button(
                "Закрыть",
                use_container_width=True,
                key="analysis_manager_missing_close",
            )
            if close and on_close:
                on_close()
            return

        defaults = build_analysis_form_defaults(analysis)
        values = render_analysis_form(
            form_key=f"analysis_manager_{analysis_id}",
            defaults=defaults,
        )
        save_clicked = st.button(
            "Сохранить",
            type="primary",
            use_container_width=True,
            key=f"analysis_manager_save_{analysis_id}",
        )
        close_clicked = st.button(
            "Закрыть",
            use_container_width=True,
            key=f"analysis_manager_close_{analysis_id}",
        )
        if save_clicked:
            payload = serialize_analysis_values(values)
            if not payload.get("asset"):
                st.error("Укажите инструмент для анализа.")
            else:
                try:
                    update_analysis(analysis_id, payload)
                    st.success("Анализ обновлён.")
                    if on_saved:
                        on_saved()
                except Exception as exc:  # pragma: no cover
                    st.error(f"Не удалось обновить анализ: {exc}")
        if close_clicked and on_close:
            on_close()

    _dialog()
