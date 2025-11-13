from typing import Callable, Optional

import streamlit as st

from .analysis_form import (
    build_analysis_form_defaults,
    render_analysis_form,
    serialize_analysis_values,
)
from db import add_analysis


def render_analysis_creator_dialog(
    *,
    on_created: Optional[Callable[[int], None]] = None,
    on_cancel: Optional[Callable[[], None]] = None,
) -> None:
    @st.dialog("Создание анализа")
    def _dialog() -> None:
        defaults = build_analysis_form_defaults()
        values = render_analysis_form(
            form_key="analysis_creator",
            defaults=defaults,
        )
        create_clicked = st.button(
            "Создать",
            type="primary",
            use_container_width=True,
            key="analysis_creator_submit",
        )
        cancel_clicked = st.button(
            "Отмена",
            use_container_width=True,
            key="analysis_creator_cancel",
        )
        if create_clicked:
            payload = serialize_analysis_values(values)
            if not payload.get("asset"):
                st.error("Укажите инструмент для анализа.")
            else:
                try:
                    new_id = add_analysis(payload)
                    st.success("Анализ создан.")
                    if on_created:
                        on_created(new_id)
                except Exception as exc:  # pragma: no cover
                    st.error(f"Не удалось создать анализ: {exc}")
        if cancel_clicked and on_cancel:
            on_cancel()

    _dialog()
