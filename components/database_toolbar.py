from typing import Dict, Iterable, List, Optional, Tuple

import streamlit as st

from utils.session_state import (
    EntityName,
    get_visible_tab,
    open_entity_dialog,
    update_period_state,
)


# --- Верхняя панель с выбором периода и запуском создания сущностей ---
def render_database_toolbar(
    *,
    tab_definitions: Iterable[Tuple[str, str]],
    session_prefix: str,
    label: str = "Период",
    entity_name: Optional[EntityName] = None,
):
    tab_definitions = list(tab_definitions)
    if not tab_definitions:
        raise ValueError("tab_definitions must not be empty")
    resolved_entity = entity_name
    entity_by_prefix: Dict[str, EntityName] = {
        "trades": "trade",
        "analysis": "analysis",
    }
    if resolved_entity is None:
        resolved_entity = entity_by_prefix.get(session_prefix)
    if resolved_entity is None:
        raise ValueError(
            "entity_name is required when session_prefix is not recognized"
        )

    default_tab_key = tab_definitions[0][1]
    period_col, _, actions_col = st.columns(
        [0.5, 0.3, 0.2], vertical_alignment="bottom"
    )

    # --- Сегментированный контрол выбора периода ---
    with period_col:
        period_labels: List[str] = [label for label, _ in tab_definitions]
        period_key = f"{session_prefix}_period_control"

        def period_on_change():
            if st.session_state.get(period_key) is None:
                st.session_state[period_key] = period_labels[0]
                return

        selected_label = st.segmented_control(
            label,
            options=period_labels,
            default=period_labels[0],
            key=period_key,
            width="stretch",
            on_change=period_on_change
        )

    # --- Блок действий (пока только Create) ---
    with actions_col:
        if st.button(
            "Create",
            type="primary",
            key=f"{session_prefix}_btn_create",
            width="stretch",
        ):
            open_entity_dialog(resolved_entity, "create")

    # --- Фиксация изменения таба для дальнейшей логики страниц ---
    label_to_key = {label: key for label, key in tab_definitions}
    selected_tab_key = label_to_key.get(selected_label, default_tab_key)
    previous_tab_key = get_visible_tab(session_prefix, default_tab_key)
    tab_changed = previous_tab_key != selected_tab_key

    update_period_state(
        session_prefix,
        label=selected_label,
        tab_key=selected_tab_key,
        tab_changed=tab_changed,
    )
