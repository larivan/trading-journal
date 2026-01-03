"""Custom component that renders entity data as a card gallery."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import streamlit as st

from utils.session_state import EntityName, handle_selection_change

ColumnDefinition = Dict[str, Any]

_COMPONENT_HTML = """
<div class="st-entity-gallery" data-root>
  <div class="st-entity-gallery__toolbar is-empty" data-toolbar>
    <div class="st-entity-gallery__toolbar-left">
      <span class="st-entity-gallery__selection" data-selection-text></span>
    </div>
    <div class="st-entity-gallery__toolbar-right">
      <button
        type="button"
        class="st-entity-gallery__toolbar-btn st-entity-gallery__toolbar-btn--danger"
        data-action-delete
        aria-label="Delete selected"
      >
        <span class="st-entity-gallery__toolbar-icon" aria-hidden="true">🗑</span>
      </button>
    </div>
  </div>
  <div class="st-entity-gallery__grid" data-grid></div>
  <div class="st-entity-gallery__footer" data-footer>
    <button type="button" class="st-entity-gallery__more-btn" data-action-more>
      Load more
    </button>
  </div>
</div>
""".strip()

_COMPONENT_CSS = """
:host {
  width: 100%;
  box-sizing: border-box;
}
.st-entity-gallery {
  box-sizing: border-box;
  width: 100%;
  padding: 0.25rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  position: relative;
}
.st-entity-gallery *,
.st-entity-gallery *::before,
.st-entity-gallery *::after {
  box-sizing: border-box;
}
.st-entity-gallery__toolbar {
  align-self: flex-start;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.25rem 0.6rem 0.3rem;
  border-radius: 0.5rem;
  background: #fff;
  border: 1px solid rgba(49, 51, 63, 0.08);
  font-size: 0.85rem;
  max-width: 100%;
  position: absolute;
  left: 0;
  bottom: calc(100% + 6px);
  z-index: 1;
  box-shadow: -2px 2px 5px #eeeeee;
}
.st-entity-gallery__toolbar.is-empty {
  visibility: hidden;
  opacity: 0;
  pointer-events: none;
}
.st-entity-gallery__toolbar.is-hidden {
  display: none;
}
.st-entity-gallery__toolbar-left {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--st-color-text-light, rgba(49, 51, 63, 0.65));
}
.st-entity-gallery__toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.st-entity-gallery__toolbar-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
}
.st-entity-gallery__selection {
  white-space: nowrap;
}
.st-entity-gallery__toolbar-btn {
  appearance: none;
  border-radius: 999px;
  border: 1px solid transparent;
  padding: 0.25rem 0.8rem;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  background: #fff;
  color: var(--st-color-text, #1c1c1c);
  transition: background 120ms ease, color 120ms ease, border-color 120ms ease,
    box-shadow 120ms ease, opacity 120ms ease;
}
.st-entity-gallery__toolbar-btn--danger {
  background: transparent;
  border-color: rgba(49, 51, 63, 0.2);
  color: rgba(49, 51, 63, 0.75);
}
.st-entity-gallery__toolbar-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}
.st-entity-gallery__grid {
  width: 100%;
  display: grid;
  gap: 0.6rem;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}
.st-entity-gallery__card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.6rem 0.75rem;
  border-radius: 0.6rem;
  background: #fff;
  border: 1px solid rgba(49, 51, 63, 0.08);
  transition: background 120ms ease, border-color 120ms ease, box-shadow 120ms ease;
}
.st-entity-gallery__card:hover {
  background: rgba(48, 115, 255, 0.03);
  border-color: rgba(48, 115, 255, 0.2);
  box-shadow: 0 1px 4px rgba(49, 51, 63, 0.12);
}
.st-entity-gallery__card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.st-entity-gallery__checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  border-radius: 0.3rem;
  border: 1px solid rgba(49, 51, 63, 0.35);
  background: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: border-color 120ms ease, background 120ms ease, box-shadow 120ms ease;
}
.st-entity-gallery__checkbox::after {
  content: "✓";
  font-size: 0.78rem;
  color: #fff;
  opacity: 0;
  transform: scale(0.8);
  transition: opacity 120ms ease, transform 120ms ease;
}
.st-entity-gallery__checkbox:checked {
  background: var(--st-primary-color, #3073ff);
  border-color: var(--st-primary-color, #3073ff);
  box-shadow: 0 0 0 1px rgba(48, 115, 255, 0.25);
}
.st-entity-gallery__checkbox:checked::after {
  opacity: 1;
  transform: scale(1);
}
.st-entity-gallery__card-actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.st-entity-gallery__open-btn {
  appearance: none;
  border-radius: 999px;
  border: 1px solid rgba(49, 51, 63, 0.25);
  padding: 0.25rem 0.9rem;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  background: rgba(49, 51, 63, 0.06);
  color: var(--st-color-text, #1c1c1c);
  transition: background 120ms ease, color 120ms ease, box-shadow 120ms ease,
    border-color 120ms ease, opacity 120ms ease;
}
.st-entity-gallery__open-btn:hover {
  box-shadow: 0 1px 3px rgba(49, 51, 63, 0.2);
  background: rgba(49, 51, 63, 0.14);
}
.st-entity-gallery__open-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
}
.st-entity-gallery__card-body {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.st-entity-gallery__title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--st-color-text, #1c1c1c);
}
.st-entity-gallery__subtitle {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--st-color-text-light, rgba(49, 51, 63, 0.65));
}
.st-entity-gallery__text {
  font-size: 0.85rem;
  line-height: 1.4;
  color: var(--st-color-text, #1c1c1c);
  white-space: pre-wrap;
}
.st-entity-gallery__meta {
  display: grid;
  gap: 0.35rem;
  padding-top: 0.35rem;
  border-top: 1px dashed rgba(49, 51, 63, 0.12);
}
.st-entity-gallery__meta-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr);
  gap: 0.5rem;
  align-items: baseline;
}
.st-entity-gallery__meta-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--st-color-text-light, rgba(49, 51, 63, 0.65));
}
.st-entity-gallery__meta-value {
  font-size: 0.82rem;
  color: var(--st-color-text, #1c1c1c);
  text-align: right;
  word-break: break-word;
}
.st-entity-gallery__footer {
  display: flex;
  justify-content: flex-start;
  padding-top: 0.25rem;
}
.st-entity-gallery__more-btn {
  appearance: none;
  border-radius: 999px;
  border: 1px dashed var(--st-primary-color);
  padding: 0.25rem 0.9rem;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  background: transparent;
  color: var(--st-primary-color);
  transition: background 120ms ease, color 120ms ease, border-color 120ms ease;
}
.st-entity-gallery__more-btn:hover {
  background: rgba(48, 115, 255, 0.06);
}
@media (max-width: 640px) {
  .st-entity-gallery__toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .st-entity-gallery__toolbar-right {
    justify-content: flex-end;
  }
  .st-entity-gallery__meta-row {
    grid-template-columns: minmax(0, 1fr);
  }
  .st-entity-gallery__meta-value {
    text-align: left;
  }
}
""".strip()

_COMPONENT_JS = """
const template = document.createElement("template");
template.innerHTML = `
<div class="st-entity-gallery" data-root>
  <div class="st-entity-gallery__toolbar" data-toolbar>
    <div class="st-entity-gallery__toolbar-left">
      <span class="st-entity-gallery__selection" data-selection-text></span>
    </div>
    <div class="st-entity-gallery__toolbar-right">
      <button type="button" class="st-entity-gallery__toolbar-btn st-entity-gallery__toolbar-btn--danger" data-action-delete aria-label="Delete selected">
        <span class="st-entity-gallery__toolbar-icon" aria-hidden="true">🗑</span>
      </button>
    </div>
  </div>
  <div class="st-entity-gallery__grid" data-grid></div>
  <div class="st-entity-gallery__footer" data-footer>
    <button type="button" class="st-entity-gallery__more-btn" data-action-more>
      Load more
    </button>
  </div>
</div>
`;

const ensureRoot = (parentElement) => {
  if (!parentElement) {
    return null;
  }
  let root = parentElement.querySelector("[data-root]");
  if (!root) {
    parentElement.innerHTML = "";
    parentElement.appendChild(template.content.cloneNode(true));
    root = parentElement.querySelector("[data-root]");
  }
  return root;
};

const toArray = (value) => {
  if (!value) {
    return [];
  }
  return Array.isArray(value) ? value : [value];
};

const normalizeColumns = (columns) => {
  if (!Array.isArray(columns)) {
    return [];
  }
  const allowedRoles = new Set(["title", "subtitle", "text", "detail", "hidden"]);
  const roleAlias = { body: "text" };
  return columns.map((col, index) => {
    const rawRole = typeof col?.role === "string" ? col.role.toLowerCase() : "";
    const mappedRole = roleAlias[rawRole] || rawRole;
    const role = col?.hidden ? "hidden" : allowedRoles.has(mappedRole) ? mappedRole : "detail";
    return {
      key: col?.key ?? String(index),
      label: col?.label ?? String(col?.key ?? index + 1),
      role,
    };
  });
};

const normalizeRows = (rows) => {
  if (!Array.isArray(rows)) {
    return [];
  }
  return rows
    .map((row) => ({
      id: row?.id ?? null,
      cells: row?.cells && typeof row.cells === "object" ? row.cells : {},
    }))
    .filter((row) => row.id !== null && row.id !== undefined);
};

const sanitizeValue = (value) => {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value);
};

const buildCardData = (row, columns) => {
  let title = "";
  let subtitle = "";
  const textBlocks = [];
  const details = [];

  columns.forEach((col) => {
    if (col.role === "hidden") {
      return;
    }
    const raw = Object.prototype.hasOwnProperty.call(row.cells, col.key)
      ? row.cells[col.key]
      : "";
    const value = sanitizeValue(raw).trim();
    if (!value) {
      return;
    }
    if (col.role === "title") {
      if (!title) {
        title = value;
      }
      return;
    }
    if (col.role === "subtitle") {
      if (!subtitle) {
        subtitle = value;
      }
      return;
    }
    if (col.role === "text") {
      textBlocks.push(value);
      return;
    }
    details.push({ label: col.label ?? col.key, value });
  });

  return { title, subtitle, textBlocks, details };
};

const updateToolbar = (toolbarEl, selectionTextEl, deleteButton, selectedIds, allowSelection) => {
  if (!toolbarEl) {
    return;
  }
  if (!allowSelection) {
    toolbarEl.classList.add("is-hidden");
    return;
  }
  toolbarEl.classList.remove("is-hidden");
  const count = selectedIds.size;
  if (count === 0) {
    toolbarEl.classList.add("is-empty");
    if (deleteButton) {
      deleteButton.disabled = true;
    }
    if (selectionTextEl) {
      selectionTextEl.textContent = "";
    }
    return;
  }
  toolbarEl.classList.remove("is-empty");
  if (selectionTextEl) {
    selectionTextEl.textContent = `${count} selected`;
  }
  if (deleteButton) {
    deleteButton.disabled = false;
  }
};

const renderGallery = ({
  gridEl,
  footerEl,
  rows,
  columns,
  page,
  pageSize,
  selectedIds,
  allowSelection,
  allowOpen,
  onSelectionChange,
  setStateValue,
  setTriggerValue,
}) => {
  if (!gridEl) {
    return;
  }

  const currentPage = Number.isInteger(page) && page >= 0 ? page : 0;
  const size = Number.isInteger(pageSize) && pageSize > 0 ? pageSize : 12;
  const visibleCount = (currentPage + 1) * size;
  const visibleRows = rows.slice(0, visibleCount);
  const hasMore = rows.length > visibleRows.length;

  gridEl.innerHTML = "";

  visibleRows.forEach((row) => {
    const card = document.createElement("article");
    card.className = "st-entity-gallery__card";

    const headerNeeded = allowSelection || allowOpen;
    if (headerNeeded) {
      const head = document.createElement("div");
      head.className = "st-entity-gallery__card-head";

      if (allowSelection) {
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.className = "st-entity-gallery__checkbox";
        checkbox.checked = selectedIds.has(row.id);
        checkbox.onclick = (event) => {
          const checked = event.target.checked;
          if (checked) {
            selectedIds.add(row.id);
          } else {
            selectedIds.delete(row.id);
          }
          if (typeof onSelectionChange === "function") {
            onSelectionChange();
          } else {
            setStateValue("selected_ids", Array.from(selectedIds));
          }
        };
        head.appendChild(checkbox);
      } else {
        const spacer = document.createElement("div");
        spacer.style.flex = "1 1 auto";
        head.appendChild(spacer);
      }

      if (allowOpen) {
        const actions = document.createElement("div");
        actions.className = "st-entity-gallery__card-actions";
        const openBtn = document.createElement("button");
        openBtn.type = "button";
        openBtn.className = "st-entity-gallery__open-btn";
        openBtn.textContent = "Open";
        openBtn.onclick = (event) => {
          event.preventDefault();
          setTriggerValue("open", row.id);
        };
        actions.appendChild(openBtn);
        head.appendChild(actions);
      }

      card.appendChild(head);
    }

    const body = document.createElement("div");
    body.className = "st-entity-gallery__card-body";
    const cardData = buildCardData(row, columns);

    if (cardData.title) {
      const titleEl = document.createElement("div");
      titleEl.className = "st-entity-gallery__title";
      titleEl.textContent = cardData.title;
      body.appendChild(titleEl);
    }
    if (cardData.subtitle) {
      const subtitleEl = document.createElement("div");
      subtitleEl.className = "st-entity-gallery__subtitle";
      subtitleEl.textContent = cardData.subtitle;
      body.appendChild(subtitleEl);
    }
    if (Array.isArray(cardData.textBlocks) && cardData.textBlocks.length) {
      cardData.textBlocks.forEach((text) => {
        const textEl = document.createElement("div");
        textEl.className = "st-entity-gallery__text";
        textEl.textContent = text;
        body.appendChild(textEl);
      });
    }

    if (Array.isArray(cardData.details) && cardData.details.length) {
      const meta = document.createElement("div");
      meta.className = "st-entity-gallery__meta";
      cardData.details.forEach((item) => {
        const rowEl = document.createElement("div");
        rowEl.className = "st-entity-gallery__meta-row";
        const labelEl = document.createElement("div");
        labelEl.className = "st-entity-gallery__meta-label";
        labelEl.textContent = item.label || "";
        const valueEl = document.createElement("div");
        valueEl.className = "st-entity-gallery__meta-value";
        valueEl.textContent = item.value || "";
        rowEl.appendChild(labelEl);
        rowEl.appendChild(valueEl);
        meta.appendChild(rowEl);
      });
      body.appendChild(meta);
    }

    card.appendChild(body);

    gridEl.appendChild(card);
  });

  if (footerEl) {
    const moreButton = footerEl.querySelector("[data-action-more]");
    footerEl.style.display = hasMore ? "flex" : "none";
    if (moreButton) {
      moreButton.onclick = (event) => {
        event.preventDefault();
        const nextPage = currentPage + 1;
        setStateValue("page", nextPage);
      };
    }
  }
};

export default function (component) {
  const { parentElement, data = {}, setStateValue, setTriggerValue } = component;
  const root = ensureRoot(parentElement);
  if (!root) {
    return;
  }

  const toolbarEl = root.querySelector("[data-toolbar]");
  const selectionTextEl = root.querySelector("[data-selection-text]");
  const deleteButton = root.querySelector("[data-action-delete]");
  const gridEl = root.querySelector("[data-grid]");
  const footerEl = root.querySelector("[data-footer]");

  const rows = normalizeRows(data.rows);
  const columns = normalizeColumns(data.columns);
  const pageSize = Number.isInteger(data.pageSize) && data.pageSize > 0 ? data.pageSize : 12;
  const page = Number.isInteger(data.page) && data.page >= 0 ? data.page : 0;
  const selectedIds = new Set(toArray(data.selectedIds));
  const allowSelection = data.allowSelection !== false;
  const allowOpen = data.allowOpen === true;

  const onSelectionChange = () => {
    updateToolbar(toolbarEl, selectionTextEl, deleteButton, selectedIds, allowSelection);
    setStateValue("selected_ids", Array.from(selectedIds));
  };

  if (toolbarEl && deleteButton && selectionTextEl) {
    deleteButton.onclick = (event) => {
      event.preventDefault();
      if (!selectedIds.size) {
        return;
      }
      const ids = Array.from(selectedIds);
      setTriggerValue("delete", ids);
    };
  }

  updateToolbar(toolbarEl, selectionTextEl, deleteButton, selectedIds, allowSelection);

  renderGallery({
    gridEl,
    footerEl,
    rows,
    columns,
    page,
    pageSize,
    selectedIds,
    allowSelection,
    allowOpen,
    onSelectionChange,
    setStateValue,
    setTriggerValue,
  });
}
""".strip()

_entity_gallery_component = st.components.v2.component(
    "entity_gallery",
    html=_COMPONENT_HTML,
    css=_COMPONENT_CSS,
    js=_COMPONENT_JS,
)


def _format_cell_value(value: Any, column: ColumnDefinition) -> str:
    """Format a column value as text for display."""
    if value is None:
        return ""
    formatter = column.get("format")
    if callable(formatter):
        try:
            return str(formatter(value))
        except Exception:
            return str(value)
    return str(value)


def _normalize_columns(
    columns: Sequence[ColumnDefinition],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    normalized: List[Dict[str, Any]] = []
    order: List[str] = []
    for index, column in enumerate(columns):
        field = column.get("field")
        col_key = column.get("id") or column.get(
            "key") or field or f"col_{index}"
        label = column.get("label") or field or col_key
        role = column.get("role")
        normalized.append(
            {
                "key": str(col_key),
                "label": str(label),
                "field": field,
                "role": str(role) if role else None,
                "hidden": bool(column.get("hidden")),
                "compute": column.get("compute"),
                "format": column.get("format"),
            }
        )
        order.append(str(col_key))
    return normalized, order


def _build_rows_payload(
    *,
    rows: Sequence[Dict[str, Any]],
    id_field: str,
    columns: Sequence[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[Any, Dict[str, Any]]]:
    processed_rows: List[Dict[str, Any]] = []
    id_to_row: Dict[Any, Dict[str, Any]] = {}
    for row in rows:
        row_id = row.get(id_field)
        if row_id is None:
            continue
        id_to_row[row_id] = row
        cells: Dict[str, Any] = {}
        for col in columns:
            col_key = col["key"]
            field = col.get("field")
            value: Any
            compute = col.get("compute")
            if callable(compute):
                try:
                    value = compute(row)
                except Exception:
                    value = None
            elif field:
                value = row.get(field)
            else:
                value = None
            cells[col_key] = _format_cell_value(value, col)
        processed_rows.append({"id": row_id, "cells": cells})
    return processed_rows, id_to_row


def render_entity_gallery(
    *,
    entity_name: EntityName,
    key: str,
    rows: Sequence[Dict[str, Any]],
    columns: Sequence[ColumnDefinition],
    id_field: str = "id",
    empty_message: str = "No data to display.",
    page_size: int = 12,
    on_open: Optional[Callable[[Dict[str, Any]], None]] = None,
    on_delete: Optional[Callable[[List[Any]], None]] = None,
    enable_selection: Optional[bool] = None,
) -> None:
    """Render a gallery of cards for arbitrary entities.

    Columns may specify role: title, subtitle, text, detail, hidden.
    """
    if not rows:
        st.info(empty_message)
        handle_selection_change(entity_name, [])
        return

    component_state = st.session_state.get(key, {})
    initial_selected = (
        list(component_state.get("selected_ids") or [])
        if isinstance(component_state, dict)
        else []
    )
    raw_page = component_state.get("page") if isinstance(
        component_state, dict) else 0
    initial_page = int(raw_page) if isinstance(
        raw_page, int) and raw_page >= 0 else 0

    normalized_columns, _ = _normalize_columns(columns)
    rows_payload, id_to_row = _build_rows_payload(
        rows=rows,
        id_field=id_field,
        columns=normalized_columns,
    )

    selection_enabled = True if enable_selection is None else bool(
        enable_selection)

    callbacks: Dict[str, Callable[[], None]] = {
        "on_selected_ids_change": lambda: None,
        "on_open_change": lambda: None,
        "on_delete_change": lambda: None,
        "on_page_change": lambda: None,
    }

    result = _entity_gallery_component(
        key=key,
        data={
            "rows": rows_payload,
            "columns": [
                {
                    "key": col["key"],
                    "label": col["label"],
                    "role": col.get("role"),
                    "hidden": col.get("hidden", False),
                }
                for col in normalized_columns
            ],
            "pageSize": max(1, int(page_size)),
            "page": initial_page,
            "selectedIds": initial_selected if selection_enabled else [],
            "allowSelection": selection_enabled,
            "allowOpen": bool(on_open),
        },
        default={
            "selected_ids": initial_selected if selection_enabled else [],
            "page": initial_page,
        },
        **callbacks,
    )

    if not isinstance(result, dict):
        handle_selection_change(entity_name, initial_selected)
        return

    selected_ids = result.get("selected_ids") or initial_selected
    if not isinstance(selected_ids, list):
        selected_ids = initial_selected

    open_id = result.get("open")
    delete_ids = result.get("delete")

    if on_open is not None and open_id is not None:
        row = id_to_row.get(open_id)
        if row is not None:
            on_open(row)
            st.rerun()

    if on_delete is not None and isinstance(delete_ids, list) and delete_ids:
        on_delete(delete_ids)

    if selection_enabled:
        handle_selection_change(entity_name, selected_ids)
    else:
        handle_selection_change(entity_name, [])


__all__ = ["render_entity_gallery", "ColumnDefinition"]
