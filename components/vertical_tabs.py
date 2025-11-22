"""Кастомный компонент вертикальных вкладок на базе streamlit.components.v2."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Sequence, Tuple

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

TabItem = Dict[str, Any]

_COMPONENT_HTML = """
<div class="st-vtabs" data-root>
  <div class="st-vtabs__label" data-label></div>
  <div class="st-vtabs__list" data-list></div>
  <div class="st-vtabs__add" data-add></div>
</div>
""".strip()

_COMPONENT_CSS = """
:host {
  width: 100%;
}
.st-vtabs {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
}
.st-vtabs__label {
  color: var(--st-color-text-light, rgba(49, 51, 63, 0.6));
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.st-vtabs__list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.st-vtabs__row {
  position: relative;
}
.st-vtabs__tab {
  display: block;
  width: 100%;
  appearance: none;
  border: 1px solid rgba(31, 42, 58, 0.2);
  border-radius: 0.6rem;
  background: transparent;
  color: var(--st-color-text, #1c1c1c);
  padding: 0.65rem 0.85rem;
  text-align: left;
  font-weight: 600;
  cursor: pointer;
  transition: background 120ms ease, border-color 120ms ease, color 120ms ease;
}
.st-vtabs__row.is-selected .st-vtabs__tab {
  background-color: rgba(150, 150, 202, 0.15);
  box-shadow: 0 2px 6px rgba(49, 51, 63, 0.15);
}

.st-vtabs__remove {
  display: flex;
  align-items: center;
  justify-content: center;
  appearance: none;
  border: none;
  background: #ff7a66;
  color: var(--st-color-text, #fff);
  font-size: 1.1rem;
  border-radius: 999px;
  width: 16px;
  height: 16px;
  cursor: pointer;
  position: absolute;
  top: -4px;
  right: -4px;
  transition: background 120ms ease, color 120ms ease;
}
.st-vtabs__remove:hover:not(:disabled) {
  background: #cccccc;
  color: #000;
}
.st-vtabs__remove:disabled {
  display: none;
}
.st-vtabs__add {
  display: flex;
  justify-content: center;
  margin-top: 0.5rem;
}
.st-vtabs__add-btn {
  appearance: none;
  border-radius: 999px;
  padding: 0.4rem 1.2rem;
  border: 1px dashed var(--st-primary-color);
  background: transparent;
  color: var(--st-primary-color);
  font-weight: 600;
  cursor: pointer;
  transition: background 120ms ease, color 120ms ease;
}
.st-vtabs__add-btn:hover {
  background: rgba(48, 115, 255, 0.08);
}
""".strip()

_COMPONENT_JS = """
const template = document.createElement("template");
template.innerHTML = `
<div class="st-vtabs" data-root>
  <div class="st-vtabs__label" data-label></div>
  <div class="st-vtabs__list" data-list></div>
  <div class="st-vtabs__add" data-add></div>
</div>
`;

const normalize = (value) =>
  value === null || value === undefined ? "" : String(value);

const ensureRoot = (parentElement) => {
  let root = parentElement.querySelector("[data-root]");
  if (!root) {
    parentElement.innerHTML = "";
    parentElement.appendChild(template.content.cloneNode(true));
    root = parentElement.querySelector("[data-root]");
  }
  return root;
};

const updateSelection = (listEl, normalizedId) => {
  listEl.querySelectorAll(".st-vtabs__row").forEach((row) => {
    if (row.dataset.tabId === normalizedId) {
      row.classList.add("is-selected");
    } else {
      row.classList.remove("is-selected");
    }
  });
};

export default function(component) {
  const { parentElement, data = {}, setStateValue, setTriggerValue } = component;
  const tabsData = Array.isArray(data.tabs) ? data.tabs : [];
  const selectedId = normalize(data.selectedId);
  const allowAdd = Boolean(data.allowAdd);
  const allowRemove = Boolean(data.allowRemove);
  const minTabs = Number.isFinite(data.minTabs) ? data.minTabs : 1;

  if (!parentElement) {
    return;
  }

  const root = ensureRoot(parentElement);
  const labelEl = root.querySelector("[data-label]");
  const listEl = root.querySelector("[data-list]");
  const addEl = root.querySelector("[data-add]");

  if (data.label) {
    labelEl.style.display = "block";
    labelEl.textContent = data.label;
  } else {
    labelEl.style.display = "none";
    labelEl.textContent = "";
  }

  listEl.innerHTML = "";
  tabsData.forEach((tab) => {
    const tabId = normalize(tab.id);
    const row = document.createElement("div");
    row.className = "st-vtabs__row";
    row.dataset.tabId = tabId;
    if (tabId === selectedId) {
      row.classList.add("is-selected");
    }

    const tabButton = document.createElement("button");
    tabButton.type = "button";
    tabButton.className = "st-vtabs__tab";
    tabButton.textContent = tab.label ?? String(tab.id ?? "");
    tabButton.onclick = (event) => {
      event.preventDefault();
      if (normalize(component.data?.selectedId) === tabId) {
        return;
      }
      const nextSelected = tab.id;
      updateSelection(listEl, tabId);
      setStateValue("selected_id", nextSelected);
    };

    row.appendChild(tabButton);

    if (allowRemove) {
      const removeButton = document.createElement("button");
      removeButton.type = "button";
      removeButton.className = "st-vtabs__remove";
      removeButton.textContent = tab.removeLabel || data.removeLabel || "×";
      const shouldDisable =
        tabsData.length <= minTabs || Boolean(tab.disableRemove);
      removeButton.disabled = shouldDisable;
      removeButton.onclick = (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (removeButton.disabled) {
          return;
        }
        setTriggerValue("remove", tab.id);
      };
      row.appendChild(removeButton);
    }

    listEl.appendChild(row);
  });

  addEl.innerHTML = "";
  if (allowAdd) {
    const addButton = document.createElement("button");
    addButton.type = "button";
    addButton.className = "st-vtabs__add-btn";
    addButton.textContent = data.addLabel || "Добавить";
    addButton.onclick = (event) => {
      event.preventDefault();
      setTriggerValue("add", true);
    };
    addEl.appendChild(addButton);
  }
}
""".strip()

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
    add_label: str = "Добавить",
    remove_label: str = "×",
    min_tabs: int = 1,
    on_add: Optional[Callable[[], None]] = None,
    on_remove: Optional[Callable[[TabItem], None]] = None,
) -> Tuple[Optional[TabItem], DeltaGenerator]:
    """Отрисовывает вертикальные вкладки и возвращает активный таб + контейнер."""

    tab_list = list(tabs)
    if not tab_list:
        placeholder = st.container()
        placeholder.info("Нет вкладок для отображения.")
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
        on_add()

    remove_target = result.get("remove")
    if on_remove and remove_target is not None:
        on_remove(tab_lookup.get(remove_target, {"id": remove_target}))

    return tab_lookup.get(selected_id), content_col.container()


def _resolve_selected_id(key: str, tabs: Sequence[TabItem]) -> Any:
    stored = st.session_state.get(key, {})
    if isinstance(stored, dict):
        existing = stored.get("selected_id")
        if existing in {tab["id"] for tab in tabs}:
            return existing
    return tabs[0]["id"]


__all__ = ["render_vertical_tabs"]
