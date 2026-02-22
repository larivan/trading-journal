"""Кастомный компонент для выбора и привязки заметок к сущностям со стадированием."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence

import streamlit as st

from config import NOTE_DIALOG_NAME, NOTE_ID_STATE
from db import delete_note, list_analysis_stage_notes, list_notes, list_trade_notes
from utils.auth import get_current_user_id
from utils.session_state import open_dialog, set_previous_dialog
from helpers import get_excerpt

_DIR = Path(__file__).parent
_COMPONENT_HTML = (_DIR / "template.html").read_text(encoding="utf-8")
_COMPONENT_CSS = (_DIR / "styles.css").read_text(encoding="utf-8")
_COMPONENT_JS = (_DIR / "script.js").read_text(encoding="utf-8")

EntityType = Literal["trade", "analysis_stage"]


def _note_payload(note: Dict[str, Any], *, limit: int) -> Dict[str, Any]:
    return {
        "id": note.get("id"),
        "excerpt": get_excerpt(note.get("body"), limit),
        "date_local": note.get("date_local"),
        "time_local": note.get("time_local"),
    }


def _list_attached_notes(entity_type: EntityType, entity_id: int) -> List[Dict[str, Any]]:
    if entity_type == "trade":
        return list_trade_notes(entity_id)
    if entity_type == "analysis_stage":
        return list_analysis_stage_notes(entity_id)
    raise ValueError(f"Unsupported entity type: {entity_type}")


def _state_keys(state_key: str) -> Dict[str, str]:
    return {
        "staged_notes": f"{state_key}__staged_notes",
        "last_event": f"{state_key}__last_event",
        "pending_attach": f"{state_key}__pending_attach",
    }


def clear_note_selector_state(state_key: str) -> None:
    """Удаляет кеш привязок по ключу состояния."""
    keys = _state_keys(state_key)
    for key in keys.values():
        st.session_state.pop(key, None)


_note_selector_component = st.components.v2.component(
    "note_selector",
    html=_COMPONENT_HTML,
    css=_COMPONENT_CSS,
    js=_COMPONENT_JS,
)


def render_note_selector(
    *,
    entity_type: EntityType,
    entity_id: Optional[int] = None,
    state_key: str,
    previous_dialog_name: Optional[str] = None,
    excerpt_limit: int = 120,
    base_notes: Optional[Sequence[Dict[str, Any]]] = None,
) -> List[int]:
    """Рендерит селектор и возвращает стадированный список id заметок."""
    keys = _state_keys(state_key)
    if base_notes is not None:
        base_notes_value = list(base_notes)
    elif entity_id:
        base_notes_value = _list_attached_notes(entity_type, entity_id)
    else:
        base_notes_value = []
    all_notes = list_notes(get_current_user_id(), order_by="date_local", ascending=False)

    base_ids = [note.get("id")
                for note in base_notes_value if note.get("id") is not None]
    staged_ids = st.session_state.get(keys["staged_notes"])
    if not isinstance(staged_ids, list):
        staged_ids = list(base_ids)

    # Автопривязка только что созданной заметки после возврата из Note Manager
    pending_attach = bool(st.session_state.get(keys["pending_attach"]))
    created_note_id = st.session_state.get(NOTE_ID_STATE)
    if pending_attach and created_note_id is not None:
        try:
            created_id_int = int(created_note_id)
        except (TypeError, ValueError):
            created_id_int = None
        if created_id_int is not None and created_id_int not in staged_ids:
            staged_ids = [created_id_int] + staged_ids
            st.session_state[keys["staged_notes"]] = staged_ids
        st.session_state[keys["pending_attach"]] = False

    note_pool = {note["id"]: _note_payload(
        note, limit=excerpt_limit) for note in all_notes}
    staged_payload = [note_pool[nid] for nid in staged_ids if nid in note_pool]
    all_payload = list(note_pool.values())

    callbacks = {
        "on_event_change": lambda: None,
    }

    result = _note_selector_component(
        key=state_key,
        data={
            "attached": staged_payload,
            "all_notes": all_payload,
            "excerpt_limit": excerpt_limit,
        },
        default={
            "event": None,
        },
        **callbacks,
    )

    if isinstance(result, dict):
        event = result.get("event")
        if isinstance(event, dict):
            event_id = event.get("event_id")
            if event_id is not None and st.session_state.get(keys["last_event"]) == event_id:
                return staged_ids
            if event_id is not None:
                st.session_state[keys["last_event"]] = event_id

            event_type = event.get("type")
            note_id = event.get("note_id")
            ids = event.get("ids") or []

            if event_type == "attach" and note_id is not None:
                nid = int(note_id)
                if nid not in staged_ids:
                    staged_ids = [nid] + staged_ids
                st.session_state[keys["staged_notes"]] = staged_ids
                st.rerun()

            if event_type == "detach" and ids:
                staged_ids = [nid for nid in staged_ids if nid not in set(
                    int(x) for x in ids)]
                st.session_state[keys["staged_notes"]] = staged_ids
                st.rerun()

            if event_type == "delete" and ids:
                remove_ids = set(int(x) for x in ids)
                for nid in remove_ids:
                    try:
                        delete_note(int(nid))
                    except Exception:
                        continue
                staged_ids = [
                    nid for nid in staged_ids if nid not in remove_ids]
                st.session_state[keys["staged_notes"]] = staged_ids
                st.rerun()

            if event_type == "open" and note_id is not None:
                st.session_state[NOTE_ID_STATE] = int(note_id)
                if previous_dialog_name:
                    set_previous_dialog(previous_dialog_name)
                open_dialog(NOTE_DIALOG_NAME)
                st.rerun()

            if event_type == "create":
                st.session_state.pop(NOTE_ID_STATE, None)
                st.session_state[keys["pending_attach"]] = True
                if previous_dialog_name:
                    set_previous_dialog(previous_dialog_name)
                open_dialog(NOTE_DIALOG_NAME)
                st.rerun()

    st.session_state[keys["staged_notes"]] = staged_ids
    return staged_ids


__all__ = ["render_note_selector", "clear_note_selector_state", "EntityType"]
