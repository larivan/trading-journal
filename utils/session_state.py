from __future__ import annotations

from datetime import date
from typing import Any, Callable, Dict, Iterable, Literal, Optional, Sequence, Tuple

import streamlit as st

from components.entity_filters import tab_date_range
# --- Базовые типы и конфигурация сущностей ---
EntityName = Literal["trade", "analysis", "note"]
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
    "note": {
        "selected_key": "selected_note_id",
        "dialogs": {
            "create": "show_create_note",
            "edit": "show_edit_note",
        },
    },
}

_ENTITY_SESSION_PREFIX: Dict[EntityName, str] = {
    "trade": "trades",
    "analysis": "analysis",
    "note": "notes",
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


def switch_to_edit_dialog(entity: EntityName, entity_id: int) -> None:
    """Переключает интерфейс на режим редактирования созданной сущности."""
    set_selected_entity(entity, entity_id)
    open_entity_dialog(entity, "edit")


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


# --- Композитные хелперы для страниц сущностей ---
CustomFilterRenderer = Callable[
    [Optional[Dict[str, Any]], Optional[Tuple[Optional[date], Optional[date]]]],
    Tuple[Dict[str, Any], Tuple[Optional[date], Optional[date]]],
]


def init_entity_state(
    *,
    entity_name: EntityName,
    default_range: Tuple[date, date],
) -> None:
    """Гарантирует наличие базовых ключей состояния для сущности."""
    selected_key = _ENTITY_CONFIG[entity_name]["selected_key"]
    st.session_state.setdefault(selected_key, None)
    for flag in _ENTITY_CONFIG[entity_name]["dialogs"].values():
        st.session_state.setdefault(flag, False)
    prefix = _ENTITY_SESSION_PREFIX[entity_name]
    st.session_state.setdefault(_filters_key(prefix), {})
    st.session_state.setdefault(_range_key(prefix), default_range)


def apply_period_filters(
    *,
    entity_name: EntityName,
    session_prefix: str,
    default_range: Tuple[date, date],
    tab_definitions: Iterable[Tuple[str, str]],
    render_custom_filters: CustomFilterRenderer,
) -> Tuple[Dict[str, Any], Optional[date], Optional[date], str]:
    """Общая логика обработки периодов и кастомных фильтров."""
    default_tab_key = tab_definitions[0][1]
    selected_tab_key = get_visible_tab(session_prefix, default_tab_key)
    tab_changed = consume_tab_change(session_prefix)
    if tab_changed:
        reset_entity_state(entity_name)
        clear_table_state(session_prefix, selected_tab_key)
    if selected_tab_key == "custom":
        filters, custom_range = render_custom_filters(
            default_range,
        )
        tab_filters = dict(filters)
        date_from, date_to = custom_range
    else:
        tab_filters = {}
        date_from, date_to = tab_date_range(selected_tab_key)
    if date_from:
        tab_filters["date_from"] = date_from.isoformat()
    if date_to:
        tab_filters["date_to"] = date_to.isoformat()
    return tab_filters, date_from, date_to, selected_tab_key


__all__ = [
    "EntityDialog",
    "EntityName",
    "clear_table_state",
    "close_entity_dialog",
    "consume_tab_change",
    "dialog_is_open",
    "get_selected_entity",
    "get_visible_tab",
    "handle_selection_change",
    "init_entity_state",
    "open_entity_dialog",
    "reset_entity_dialogs",
    "reset_entity_state",
    "apply_period_filters",
    "set_selected_entity",
    "switch_to_edit_dialog",
    "update_period_state",
]
