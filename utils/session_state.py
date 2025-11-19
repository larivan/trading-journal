from __future__ import annotations

from datetime import date
from typing import Any, Dict, Literal, Optional, Sequence, Tuple

import streamlit as st

# --- Базовые типы и конфигурация сущностей ---
EntityName = Literal["trade", "analysis"]
EntityDialog = Literal["create", "edit", "delete"]


class _EntityConfig(Dict[str, Any]):
    selected_key: str
    dialogs: Dict[str, str]


_ENTITY_CONFIG: Dict[EntityName, Dict[str, Any]] = {
    "trade": {
        "selected_key": "selected_trade_id",
        "dialogs": {
            "create": "show_create_trade",
            "edit": "show_edit_trade",
        },
    },
    "analysis": {
        "selected_key": "selected_analysis_id",
        "dialogs": {
            "create": "show_create_analysis",
            "edit": "show_edit_analysis",
            "delete": "show_delete_analysis",
        },
    },
}


def _dialog_key(entity: EntityName, dialog: EntityDialog) -> Optional[str]:
    return _ENTITY_CONFIG[entity]["dialogs"].get(dialog)


# --- Управление выбранной сущностью и диалогами ---
def set_selected_entity(entity: EntityName, entity_id: Optional[int]) -> None:
    st.session_state[_ENTITY_CONFIG[entity]["selected_key"]] = entity_id


def get_selected_entity(entity: EntityName) -> Optional[int]:
    return st.session_state.get(_ENTITY_CONFIG[entity]["selected_key"])


def reset_entity_dialogs(entity: EntityName) -> None:
    for key in _ENTITY_CONFIG[entity]["dialogs"].values():
        st.session_state[key] = False


def reset_entity_state(entity: EntityName) -> None:
    set_selected_entity(entity, None)
    reset_entity_dialogs(entity)


def open_entity_dialog(entity: EntityName, dialog: EntityDialog) -> None:
    key = _dialog_key(entity, dialog)
    if not key:
        return
    reset_entity_dialogs(entity)
    st.session_state[key] = True


def close_entity_dialog(entity: EntityName, dialog: EntityDialog) -> None:
    key = _dialog_key(entity, dialog)
    if key:
        st.session_state[key] = False


def dialog_is_open(entity: EntityName, dialog: EntityDialog) -> bool:
    key = _dialog_key(entity, dialog)
    return bool(key and st.session_state.get(key))


def handle_selection_change(entity: EntityName, selected_ids: Sequence[Any]) -> None:
    if selected_ids:
        try:
            last_selected = selected_ids[-1]
        except IndexError:
            last_selected = None
        set_selected_entity(entity, last_selected)
        return
    if not (
        dialog_is_open(entity, "edit") or dialog_is_open(entity, "create")
    ):
        reset_entity_state(entity)


# --- Работа с периодами и табами ---
def update_period_state(
    session_prefix: str, *, label: str, tab_key: str, tab_changed: bool
) -> None:
    st.session_state[f"{session_prefix}_active_period"] = label
    st.session_state[f"{session_prefix}_visible_tab"] = tab_key
    st.session_state[f"{session_prefix}_tab_changed"] = tab_changed


def consume_tab_change(session_prefix: str) -> bool:
    key = f"{session_prefix}_tab_changed"
    return bool(st.session_state.pop(key, False))


def get_active_period_label(session_prefix: str, default_label: str) -> str:
    value = st.session_state.get(f"{session_prefix}_active_period")
    return value if isinstance(value, str) else default_label


def get_visible_tab(session_prefix: str, default_tab: str) -> str:
    value = st.session_state.get(f"{session_prefix}_visible_tab")
    return value if isinstance(value, str) else default_tab


def clear_table_state(session_prefix: str, tab_key: str) -> None:
    table_state_key = f"{session_prefix}_table_{tab_key}"
    st.session_state.pop(table_state_key, None)
    st.session_state.pop(f"{table_state_key}_selection", None)


def _filters_key(session_prefix: str) -> str:
    return f"{session_prefix}_active_filters"


def _range_key(session_prefix: str) -> str:
    return f"{session_prefix}_custom_range"


# --- Управление фильтрами и кастомными диапазонами ---
def get_entity_filters(session_prefix: str) -> Dict[str, Any]:
    stored = st.session_state.get(_filters_key(session_prefix))
    if isinstance(stored, dict):
        return dict(stored)
    st.session_state[_filters_key(session_prefix)] = {}
    return {}


def set_entity_filters(session_prefix: str, filters: Dict[str, Any]) -> None:
    st.session_state[_filters_key(session_prefix)] = dict(filters)


def get_custom_date_range(
    session_prefix: str, default_range: Tuple[date, date]
) -> Tuple[Optional[date], Optional[date]]:
    stored = st.session_state.get(_range_key(session_prefix))
    if (
        isinstance(stored, (list, tuple))
        and len(stored) == 2
    ):
        start, end = stored
        if (
            isinstance(start, (date, type(None)))
            and isinstance(end, (date, type(None)))
        ):
            st.session_state[_range_key(session_prefix)] = (start, end)
            return start, end
    st.session_state[_range_key(session_prefix)] = default_range
    return default_range


def set_custom_date_range(
    session_prefix: str, date_range: Tuple[Optional[date], Optional[date]]
) -> None:
    st.session_state[_range_key(session_prefix)] = date_range


__all__ = [
    "EntityDialog",
    "EntityName",
    "clear_table_state",
    "close_entity_dialog",
    "consume_tab_change",
    "dialog_is_open",
    "get_active_period_label",
    "get_selected_entity",
    "get_visible_tab",
    "handle_selection_change",
    "get_custom_date_range",
    "get_entity_filters",
    "open_entity_dialog",
    "reset_entity_dialogs",
    "reset_entity_state",
    "set_custom_date_range",
    "set_entity_filters",
    "set_selected_entity",
    "update_period_state",
]
