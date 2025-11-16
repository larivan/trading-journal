"""Универсальная шапка с выбором состояния и кнопками действий."""

from typing import Callable, Iterable, List, Optional

import streamlit as st


ActionConfig = Callable[[], None]


def render_entity_header(
    *,
    status_label: str,
    status_options: Iterable[str],
    current_status: Optional[str],
    status_key: str,
    actions: List[dict],
    layout_ratio: Optional[List[float]] = None,
) -> Optional[str]:
    """Рисует селект статуса и настраиваемые кнопки действий."""

    layout_ratio = layout_ratio or [0.25, 0.05, 0.7]
    status_col, spacer_col, actions_col = st.columns(
        layout_ratio,
        gap="large",
        vertical_alignment="bottom",
    )
    with status_col:
        options_list = list(status_options)
        if not options_list:
            st.warning("Нет доступных состояний")
            selected = None
        else:
            default_status = current_status if current_status in options_list else options_list[0]
            selected = st.selectbox(
                status_label,
                options_list,
                index=options_list.index(default_status),
                key=status_key,
            )

    with actions_col:
        cols = st.columns(len(actions)) if actions else []
        for idx, action in enumerate(actions):
            col = cols[idx]
            disabled = action.get("disabled", False)
            clicked = col.button(
                action.get("label", "Action"),
                type=action.get("type", "secondary"),
                use_container_width=True,
                key=action.get("key"),
                disabled=disabled,
            )
            if clicked and not disabled:
                handler = action.get("on_click")
                if callable(handler):
                    handler()

    return selected
