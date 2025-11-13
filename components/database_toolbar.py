from typing import Iterable, List, Tuple

import streamlit as st


def render_database_toolbar(
    *,
    tab_definitions: Iterable[Tuple[str, str]],
    session_prefix: str,
    label: str = "Период",
):
    tab_definitions = list(tab_definitions)
    if not tab_definitions:
        raise ValueError("tab_definitions must not be empty")

    actions_col, _, period_col = st.columns(
        [0.3, 0.2, 0.5], vertical_alignment="bottom")

    with period_col:
        period_labels: List[str] = [
            period_label for period_label, _ in tab_definitions]
        default_label = st.session_state.get(
            f"{session_prefix}_active_period", period_labels[0]
        )
        selected_label = st.segmented_control(
            label,
            options=period_labels,
            default=default_label if default_label in period_labels else period_labels[0],
            key=f"{session_prefix}_period_control",
            width="stretch",
        )

    actions_placeholder = actions_col.container()
    label_to_key = {label: key for label, key in tab_definitions}
    selected_tab_key = label_to_key.get(selected_label, tab_definitions[0][1])
    previous_tab_key = st.session_state.get(f"{session_prefix}_visible_tab")
    tab_changed = previous_tab_key != selected_tab_key

    st.session_state[f"{session_prefix}_visible_tab"] = selected_tab_key
    st.session_state[f"{session_prefix}_active_period"] = selected_label

    return selected_label, selected_tab_key, tab_changed, actions_placeholder


def render_action_buttons(
    *,
    actions_container,
    session_prefix: str,
    open_disabled: bool,
):
    with actions_container:
        create_col, open_col, delete_col = st.columns(
            3, vertical_alignment="bottom"
        )
        with create_col:
            create_clicked = st.button(
                "Создать", type="primary", key=f"{session_prefix}_btn_create", width="stretch"
            )
        with open_col:
            open_clicked = st.button(
                "Открыть",
                disabled=open_disabled,
                key=f"{session_prefix}_btn_open",
                width="stretch",
            )
        with delete_col:
            delete_clicked = st.button(
                "Удалить",
                disabled=open_disabled,
                key=f"{session_prefix}_btn_delete",
                width="stretch",
            )
    return create_clicked, open_clicked, delete_clicked
