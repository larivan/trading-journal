"""Кастомный компонент вертикальных вкладок на базе streamlit.components.v2."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence, Tuple

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

_DIR = Path(__file__).parent
_COMPONENT_HTML = (_DIR / "template.html").read_text(encoding="utf-8")
_COMPONENT_CSS = (_DIR / "styles.css").read_text(encoding="utf-8")
_COMPONENT_JS = (_DIR / "script.js").read_text(encoding="utf-8")

TabItem = Dict[str, Any]

_vertical_tabs_component = st.components.v2.component(
    "vertical_tabs",
    html=_COMPONENT_HTML,
    css=_COMPONENT_CSS,
    js=_COMPONENT_JS,
)


def render_vertical_tabs(
    *,
    key: str,
    tabs: Sequence[TabItem],
    label: Optional[str] = None,
    add_label: str = "Add",
    remove_label: str = "×",
    min_tabs: int = 1,
    on_add: Optional[Callable[[], None]] = None,
    on_remove: Optional[Callable[[TabItem], None]] = None,
) -> Tuple[Optional[TabItem], DeltaGenerator]:
    """Отрисовывает вертикальные вкладки и возвращает активный таб + контейнер."""

    tab_list = list(tabs)
    if not tab_list:
        placeholder = st.container()
        placeholder.info("No tabs to display.")
        return None, placeholder

    tab_lookup = {tab["id"]: tab for tab in tab_list}
    current_selected = _resolve_selected_id(key, tab_list)

    tabs_col, content_col = st.columns([1, 3], gap="medium")
    callbacks = {"on_selected_id_change": lambda: None}
    if on_add:
        callbacks["on_add_change"] = lambda: None
    if on_remove:
        callbacks["on_remove_change"] = lambda: None

    with tabs_col:
        serializable_tabs = [
            {
                "id": tab["id"],
                "label": tab.get("label") or str(tab["id"]),
                "removeLabel": tab.get("remove_label"),
                "disableRemove": bool(tab.get("disable_remove")),
            }
            for tab in tab_list
        ]
        result = _vertical_tabs_component(
            key=key,
            data={
                "tabs": serializable_tabs,
                "selectedId": current_selected,
                "label": label,
                "allowAdd": bool(on_add),
                "allowRemove": bool(on_remove),
                "addLabel": add_label,
                "removeLabel": remove_label,
                "minTabs": max(1, int(min_tabs)),
            },
            default={"selected_id": current_selected},
            **callbacks,
        )

    selected_id = result.get("selected_id", current_selected)
    if selected_id not in tab_lookup:
        selected_id = tab_list[0]["id"]

    add_trigger = result.get("add")
    if on_add and add_trigger:
        st.session_state[_pending_select_key(key)] = True
        on_add()
        st.rerun()

    remove_target = result.get("remove")
    if on_remove and remove_target is not None:
        on_remove(tab_lookup.get(remove_target, {"id": remove_target}))
        st.rerun()

    return tab_lookup.get(selected_id), content_col.container()


def _resolve_selected_id(key: str, tabs: Sequence[TabItem]) -> Any:
    if st.session_state.pop(_pending_select_key(key), False) and tabs:
        last_id = tabs[-1]["id"]
        st.session_state[key] = {"selected_id": last_id}
        return last_id
    stored = st.session_state.get(key, {})
    if isinstance(stored, dict):
        existing = stored.get("selected_id")
        if existing in {tab["id"] for tab in tabs}:
            return existing
    return tabs[0]["id"]


def _pending_select_key(key: str) -> str:
    return f"{key}_select_new_tab"


__all__ = ["render_vertical_tabs"]
