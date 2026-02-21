from __future__ import annotations

from typing import Any, Dict, Literal, Optional, Sequence

import streamlit as st

EntityName = Literal["trade", "analysis", "note", "account", "setup"]

_ENTITY_SELECTED_KEYS: Dict[EntityName, str] = {
    "trade": "selected_trade_id",
    "analysis": "selected_analysis_id",
    "note": "selected_note_id",
    "account": "selected_account_id",
    "setup": "selected_setup_id",
}


def _selected_key(entity: EntityName) -> str:
    return _ENTITY_SELECTED_KEYS[entity]


def get_active_dialog() -> Optional[str]:
    return st.session_state.get("active_dialog")


def open_dialog(name: str) -> None:
    st.session_state["active_dialog"] = name


def close_dialog() -> None:
    st.session_state.pop("active_dialog", None)


def dialog_is_active(name: str) -> bool:
    return get_active_dialog() == name


def get_previous_dialog() -> Optional[str]:
    return st.session_state.get("previous_dialog")


def set_previous_dialog(name) -> None:
    st.session_state["previous_dialog"] = name


def remove_previous_dialog() -> None:
    st.session_state.pop("previous_dialog", None)


def set_selected_entity(entity: EntityName, entity_id: Optional[int]) -> None:
    st.session_state[_selected_key(entity)] = entity_id


def get_selected_entity(entity: EntityName) -> Optional[int]:
    return st.session_state.get(_selected_key(entity))


def handle_selection_change(entity: EntityName, selected_ids: Sequence[Any]) -> None:
    if selected_ids:
        set_selected_entity(entity, selected_ids[-1])
        return
    set_selected_entity(entity, None)


__all__ = [
    "EntityName",
    "close_dialog",
    "dialog_is_active",
    "get_active_dialog",
    "get_selected_entity",
    "handle_selection_change",
    "open_dialog",
    "set_selected_entity",
]
