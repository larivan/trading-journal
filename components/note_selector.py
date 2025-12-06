"""Кастомный компонент для выбора и привязки заметок к сущностям со стадированием."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Sequence

import streamlit as st

from config import NOTE_DIALOG_NAME, NOTE_ID_STATE
from db import delete_note, list_analysis_stage_notes, list_notes, list_trade_notes
from utils.session_state import open_dialog, set_previous_dialog

EntityType = Literal["trade", "analysis_stage"]


def _excerpt(text: Optional[str], limit: int = 45) -> str:
    value = (text or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _note_payload(note: Dict[str, Any], *, limit: int) -> Dict[str, Any]:
    return {
        "id": note.get("id"),
        "title": (note.get("title") or "Untitled").strip(),
        "excerpt": _excerpt(note.get("body") or note.get("body_plain"), limit),
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


_COMPONENT_HTML = """
<div class="ns-root" data-root>
  <div class="ns-list" data-list></div>
  <div class="ns-actions">
    <button class="ns-btn ns-btn--primary" data-create>
      Create
    </button>
    <div class="ns-browse">
      <button class="ns-btn" data-browse-toggle>
        Browse
      </button>
      <div class="ns-popover" data-browse-panel hidden>
        <input class="ns-input" type="text" data-browse-search placeholder="Search…" />
        <div class="ns-browse-list" data-browse-list></div>
      </div>
    </div>
    <button class="ns-btn ns-bulk-action" data-unattach hidden>
      Unattach
    </button>
    <button class="ns-btn ns-btn--danger ns-bulk-action" data-delete hidden>
      Delete
    </button>
  </div>
</div>
""".strip()

_COMPONENT_CSS = """
:host, * {
  box-sizing: border-box;
}
:host {
  width: 100%;
}
.ns-root {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  width: 100%;
  padding: 0.85rem;
  border: 1px solid rgba(31, 42, 58, 0.16);
  border-radius: 0.75rem;
  background: #fff;
}
.ns-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.3rem;
  border: 1px solid rgba(31, 42, 58, 0.14);
  background: #f6f7fb;
  border-radius: 0.45rem;
  padding: 0.25rem 0.45rem;
  margin: auto;
  cursor: pointer;
  color: #1f2a3a;
  transition: background 120ms ease, border-color 120ms ease, color 120ms ease;
}
.ns-icon-btn:hover {
  background: #eef2ff;
  border-color: #c5ccff;
}
.ns-icon-btn--danger {
  background: #fff5f5;
  border-color: #f0c3c3;
  color: #c92a2a;
}
.ns-icon-btn--danger:hover {
  background: #ffe3e3;
  border-color: #e03131;
}
.ns-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.ns-empty {
  padding: 0.75rem;
  border: 2px dashed rgba(31, 42, 58, 0.18);
  border-radius: 0.55rem;
  color: rgba(31, 42, 58, 0.7);
  font-size: 0.9rem;
  text-align: center;
}
.ns-card {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 0.45rem;
  align-items: flex-start;
  padding: 0.45rem 0.55rem;
  border-radius: 0.55rem;
  border: 1px solid transparent;
  background: #f8f9fb;
  cursor: pointer;
  transition: border-color 120ms ease, background 120ms ease;
}
.ns-card:hover {
  border-color: rgba(31, 42, 58, 0.25);
}
.ns-card.is-selected {
  border-color: var(--st-primary-color, #2b79ff);
  background: #eef3ff;
}
.ns-card__checkbox {
  position: relative;
  width: 18px;
  height: 18px;
  margin-top: 2px;
}
.ns-card__checkbox input {
  position: absolute;
  inset: 0;
  margin: 0;
  opacity: 0;
}
.ns-card__checkbox span {
  display: block;
  width: 18px;
  height: 18px;
  border-radius: 4px;
  border: 1px solid rgba(31, 42, 58, 0.25);
  background: #fff;
}
.ns-card.is-selected .ns-card__checkbox span {
  border-color: var(--st-primary-color, #2b79ff);
  background: var(--st-primary-color, #2b79ff);
  box-shadow: inset 0 0 0 3px #fff;
}
.ns-card__body {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}
.ns-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: #1f2a3a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ns-excerpt {
  font-size: 0.85rem;
  color: rgba(31, 42, 58, 0.72);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ns-card__open {
  justify-self: flex-end;
}
.ns-actions {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
}
.ns-btn {
  align-self: flex-end;
  appearance: none;
  border: none;
  font-size: 14px;
  height: 40px;
  min-width: 120px;
  border-radius: 0.5rem;
  padding: 0.55rem 1.5rem;
  cursor: pointer;
  transition: opacity 120ms ease;
}
.ns-btn.ns-bulk-action[hidden] {
  display: none !important;
}
.ns-btn--danger {
  background: #fff5f5;
  border-color: #f0c3c3;
  color: #c92a2a;
}
.ns-browse {
  position: relative;
}
.ns-popover {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  width: min(320px, 90vw);
  max-height: 360px;
  padding: 0.5rem;
  border-radius: 0.55rem;
  border: 1px solid rgba(31, 42, 58, 0.18);
  background: #fff;
  box-shadow: 0 10px 30px rgba(31, 42, 58, 0.15);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  z-index: 20;
}
.ns-popover[hidden] {
  display: none !important;
}
.ns-input {
  width: 100%;
  padding: 0.35rem 0.55rem;
  border-radius: 0.45rem;
  border: 1px solid rgba(31, 42, 58, 0.22);
  font-size: 0.9rem;
}
.ns-browse-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  max-height: 260px;
  overflow: auto;
  padding-right: 0.1rem;
}
.ns-browse-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.4rem 0.45rem;
  border-radius: 0.45rem;
  border: 1px solid rgba(31, 42, 58, 0.12);
  cursor: pointer;
  transition: background 120ms ease, border-color 120ms ease;
}
.ns-browse-item:hover {
  background: #f5f7ff;
  border-color: #c5ccff;
}
.ns-browse-item__title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1f2a3a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ns-browse-item__excerpt {
  font-size: 0.82rem;
  color: rgba(31, 42, 58, 0.68);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ns-browse-item__body {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}
.ns-browse-item__pill {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  border-radius: 999px;
  padding: 0.2rem 0.5rem;
  background: #eef3ff;
  border: 1px solid #d2d9ff;
  color: #30409c;
  font-size: 0.78rem;
}
.ns-browse-item.is-attached {
  opacity: 0.4;
  cursor: not-allowed;
}
.ns-browse-item.is-attached:hover {
  background: #f8f9fb;
}
.ns-browse-item__tag {
  font-size: 0.75rem;
  color: rgba(31, 42, 58, 0.6);
}
""".strip()

_COMPONENT_JS = """
const template = document.createElement("template");
template.innerHTML = `
<div class="ns-root" data-root>
  <div class="ns-toolbar" data-toolbar hidden>
    <button class="ns-icon-btn" data-unattach title="Unattach selected">🔗✖️</button>
    <button class="ns-icon-btn ns-icon-btn--danger" data-delete title="Delete selected">🗑️</button>
  </div>
  <div class="ns-list" data-list></div>
  <div class="ns-empty" data-empty>No notes yet.</div>
  <div class="ns-actions">
    <button class="ns-btn" data-create title="Create note">
      Create
    </button>
    <div class="ns-browse">
      <button class="ns-btn" data-browse-toggle title="Browse notes">
        Browse
      </button>
      <div class="ns-popover" data-browse-panel hidden>
        <input class="ns-input" type="text" data-browse-search placeholder="Search…" />
        <div class="ns-browse-list" data-browse-list></div>
      </div>
    </div>
  </div>
</div>
`;

const ensureRoot = (parent) => {
  if (!parent) return null;
  const existing = parent.querySelector("[data-root]");
  if (existing) return existing;
  const frag = template.content.cloneNode(true);
  parent.appendChild(frag);
  return parent.querySelector("[data-root]");
};

const normalizeNotes = (items, limit) => {
  if (!Array.isArray(items)) return [];
  return items
    .map((note) => ({
      id: note.id,
      title: (note.title || "Untitled").trim(),
      excerpt: (note.excerpt || "").trim(),
      date_local: note.date_local,
      time_local: note.time_local,
    }))
    .filter((note) => note.id !== undefined && note.id !== null);
};

export default function (component) {
  const { parentElement, data = {}, setStateValue } = component;
  const root = ensureRoot(parentElement);
  if (!root) return;

  const listEl = root.querySelector("[data-list]");
  const browsePanel = root.querySelector("[data-browse-panel]");
  const browseToggle = root.querySelector("[data-browse-toggle]");
  const browseList = root.querySelector("[data-browse-list]");
  const browseSearch = root.querySelector("[data-browse-search]");
  const createBtn = root.querySelector("[data-create]");
  const unattachBtn = root.querySelector("[data-unattach]");
  const deleteBtn = root.querySelector("[data-delete]");

  let attached = normalizeNotes(data.attached || [], data.excerpt_limit);
  let allNotes = normalizeNotes(data.all_notes || [], data.excerpt_limit);
  const excerptLimit = Number(data.excerpt_limit) || 45;
  let selected = new Set();

  const emitEvent = (payload) => {
    setStateValue("event", { ...payload, event_id: Date.now() });
  };

  const updateToolbar = () => {
    const hasSelection = selected.size > 0;
    unattachBtn.hidden = !hasSelection;
    deleteBtn.hidden = !hasSelection;
  };

  const toggleBrowse = () => {
    const isHidden = browsePanel.hasAttribute("hidden");
    browsePanel.toggleAttribute("hidden", !isHidden ? true : false);
  };

  const renderList = () => {
    listEl.innerHTML = "";
    if (!attached.length) {
      const empty = document.createElement("div");
      empty.className = "ns-empty";
      empty.textContent = "No notes yet.";
      listEl.appendChild(empty);
      return;
    }

    attached.forEach((note) => {
      const card = document.createElement("div");
      card.className = "ns-card";
      if (selected.has(note.id)) {
        card.classList.add("is-selected");
      }
      card.dataset.id = note.id;

      const checkbox = document.createElement("label");
      checkbox.className = "ns-card__checkbox";
      const checkboxInput = document.createElement("input");
      checkboxInput.type = "checkbox";
      checkboxInput.checked = selected.has(note.id);
      checkboxInput.dataset.check = "true";
      const checkboxBox = document.createElement("span");
      checkbox.appendChild(checkboxInput);
      checkbox.appendChild(checkboxBox);

      const body = document.createElement("div");
      body.className = "ns-card__body";
      const title = document.createElement("div");
      title.className = "ns-title";
      title.textContent = note.title || "Untitled";
      const excerpt = document.createElement("div");
      excerpt.className = "ns-excerpt";
      excerpt.textContent = note.excerpt || "";
      body.appendChild(title);
      body.appendChild(excerpt);

      const openBtn = document.createElement("button");
      openBtn.className = "ns-icon-btn ns-card__open";
      openBtn.textContent = "Open";
      openBtn.dataset.open = "true";

      const toggleSelection = () => {
        if (selected.has(note.id)) {
          selected.delete(note.id);
        } else {
          selected.add(note.id);
        }
        renderList();
        updateToolbar();
      };

      checkboxInput.onclick = (event) => {
        event.stopPropagation();
        toggleSelection();
      };
      card.onclick = (event) => {
        const target = event.target;
        if (target && target.closest("[data-open]")) {
          return;
        }
        toggleSelection();
      };

      openBtn.dataset.open = "true";
      openBtn.onclick = (event) => {
        event.stopPropagation();
        emitEvent({ type: "open", note_id: note.id });
      };

      card.appendChild(checkbox);
      card.appendChild(body);
      card.appendChild(openBtn);
      listEl.appendChild(card);
    });
  };

  const attachNote = (noteId) => {
    if (attached.some((n) => n.id === noteId)) return;
    const found = allNotes.find((n) => n.id === noteId);
    if (!found) return;
    attached = [found, ...attached];
    renderList();
    emitEvent({ type: "attach", note_id: noteId });
  };

  const renderBrowse = (query = "") => {
    browseList.innerHTML = "";
    const q = query.trim().toLowerCase();
    allNotes
      .filter((note) => {
        if (!q) return true;
        return (
          (note.title || "").toLowerCase().includes(q) ||
          (note.excerpt || "").toLowerCase().includes(q)
        );
      })
      .forEach((note) => {
        const item = document.createElement("div");
        item.className = "ns-browse-item";
        const isAttached = attached.some((n) => n.id === note.id);
        if (isAttached) {
          item.classList.add("is-attached");
        }

        const body = document.createElement("div");
        body.className = "ns-browse-item__body";
        const title = document.createElement("div");
        title.className = "ns-browse-item__title";
        title.textContent = note.title || "Untitled";
        const excerpt = document.createElement("div");
        excerpt.className = "ns-browse-item__excerpt";
        excerpt.textContent = note.excerpt || "";
        body.appendChild(title);
        body.appendChild(excerpt);

        const meta = document.createElement("div");
        meta.className = "ns-browse-item__tag";
        const date = note.date_local || "";
        const time = note.time_local ? note.time_local.slice(0, 5) : "";
        meta.textContent = [date, time].filter(Boolean).join(" · ");

        const right = document.createElement("div");
        right.style.display = "flex";
        right.style.flexDirection = "column";
        right.style.alignItems = "flex-end";
        right.style.gap = "0.15rem";
        right.appendChild(meta);

        item.appendChild(body);
        item.appendChild(right);

        item.onclick = (event) => {
          event.stopPropagation();
          if (isAttached) return;
          attachNote(note.id);
        };

        browseList.appendChild(item);
      });
  };

  browseToggle.onclick = (event) => {
    event.preventDefault();
    toggleBrowse();
  };

  browseSearch.oninput = (event) => {
    renderBrowse(event.target.value);
  };

  createBtn.onclick = (event) => {
    event.preventDefault();
    emitEvent({ type: "create" });
  };

  unattachBtn.onclick = (event) => {
    event.preventDefault();
    if (!selected.size) return;
    const ids = Array.from(selected);
    attached = attached.filter((note) => !selected.has(note.id));
    selected = new Set();
    renderList();
    updateToolbar();
    emitEvent({ type: "detach", ids });
  };

  deleteBtn.onclick = (event) => {
    event.preventDefault();
    if (!selected.size) return;
    const ids = Array.from(selected);
    attached = attached.filter((note) => !selected.has(note.id));
    selected = new Set();
    renderList();
    updateToolbar();
    emitEvent({ type: "delete", ids });
  };

  renderList();
  renderBrowse();
  updateToolbar();
}
""".strip()

_note_selector_component = st.components.v2.component(
    "note_selector",
    html=_COMPONENT_HTML,
    css=_COMPONENT_CSS,
    js=_COMPONENT_JS,
)


def render_note_selector(
    *,
    entity_type: EntityType,
    entity_id: Optional[int],
    state_key: str,
    previous_dialog_name: Optional[str] = None,
    excerpt_limit: int = 45,
) -> List[int]:
    """Рендерит селектор и возвращает стадированный список id заметок."""
    if not entity_id:
        clear_note_selector_state(state_key)
        st.info("Save the entity first to attach notes.")
        return []

    keys = _state_keys(state_key)
    base_notes = _list_attached_notes(entity_type, entity_id)
    all_notes = list_notes(order_by="date_local", ascending=False)

    base_ids = [note.get("id") for note in base_notes if note.get("id") is not None]
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

    note_pool = {note["id"]: _note_payload(note, limit=excerpt_limit) for note in all_notes}
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
                staged_ids = [nid for nid in staged_ids if nid not in set(int(x) for x in ids)]
                st.session_state[keys["staged_notes"]] = staged_ids
                st.rerun()

            if event_type == "delete" and ids:
                remove_ids = set(int(x) for x in ids)
                for nid in remove_ids:
                    try:
                        delete_note(int(nid))
                    except Exception:
                        continue
                staged_ids = [nid for nid in staged_ids if nid not in remove_ids]
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
