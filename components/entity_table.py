"""Кастомный компонент интерактивной таблицы сущностей."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import streamlit as st

from utils.session_state import EntityName, handle_selection_change

ColumnDefinition = Dict[str, Any]

_COMPONENT_HTML = """
<div class="st-entity-table" data-root>
  <div class="st-entity-table__toolbar is-empty" data-toolbar>
    <div class="st-entity-table__toolbar-left">
      <span class="st-entity-table__selection" data-selection-text></span>
    </div>
    <div class="st-entity-table__toolbar-right">
      <button
        type="button"
        class="st-entity-table__toolbar-btn st-entity-table__toolbar-btn--danger"
        data-action-delete
        aria-label="Delete selected"
      >
        <span class="st-entity-table__toolbar-icon" aria-hidden="true">🗑</span>
      </button>
    </div>
  </div>
  <div class="st-entity-table__table-wrapper">
    <table class="st-entity-table__table" data-table></table>
  </div>
  <div class="st-entity-table__footer" data-footer>
    <button type="button" class="st-entity-table__more-btn" data-action-more>
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
.st-entity-table {
  box-sizing: border-box;
  width: 100%;
  padding: 0.25rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.st-entity-table *,
.st-entity-table *::before,
.st-entity-table *::after {
  box-sizing: border-box;
}
.st-entity-table__toolbar {
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
.st-entity-table__toolbar.is-empty {
  visibility: hidden;
  opacity: 0;
  pointer-events: none;
}
.st-entity-table__toolbar-left {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--st-color-text-light, rgba(49, 51, 63, 0.65));
}
.st-entity-table__toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.st-entity-table__toolbar-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
}
.st-entity-table__selection {
  white-space: nowrap;
}
.st-entity-table__toolbar-btn {
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
.st-entity-table__toolbar-btn--danger {
  background: transparent;
  border-color: rgba(49, 51, 63, 0.2);
  color: rgba(49, 51, 63, 0.75);
}
.st-entity-table__toolbar-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}
.st-entity-table__table-wrapper {
  width: 100%;
  overflow-x: auto;
}
.st-entity-table__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.st-entity-table__table thead {
  background: transparent;
}
.st-entity-table__table th,
.st-entity-table__table td {
  padding: 0.35rem 0.6rem;
  border-bottom: 1px solid rgba(49, 51, 63, 0.06);
  border-right: 1px solid rgba(49, 51, 63, 0.06);
  text-align: left;
  vertical-align: middle;
}
.st-entity-table__table tr > *:last-child {
  border-right: none;
}
.st-entity-table__table th {
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--st-color-text-light, rgba(49, 51, 63, 0.65));
  text-align: center;
  border-right: none;
}
.st-entity-table__table tbody tr:last-child td {
  border-bottom: none;
}
.st-entity-table__table-row {
  transition: background 120ms ease;
}
.st-entity-table__table-row:hover {
  background: rgba(48, 115, 255, 0.03);
}
.st-entity-table__cell--select {
  width: 40px;
  min-width: 40px;
  max-width: 40px;
  text-align: center;
  position: sticky;
  left: 0px;
  z-index: 2;
  border-right: none !important;
  padding-left: 0.1rem;
  transform: translateX(-10px);
}
.st-entity-table__cell--actions {
  white-space: nowrap;
  text-align: left;
  position: sticky;
  left: 40;
  width: 84px;
  z-index: 2; 
  border-left: none;
}
.st-entity-table__table thead .st-entity-table__cell--select,
.st-entity-table__table thead .st-entity-table__cell--actions {
  z-index: 3;
}
.st-entity-table__checkbox {
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
.st-entity-table__checkbox::after {
  content: "✓";
  font-size: 0.78rem;
  color: #fff;
  opacity: 0;
  transform: scale(0.8);
  transition: opacity 120ms ease, transform 120ms ease;
}
.st-entity-table__checkbox:checked {
  background: var(--st-primary-color, #3073ff);
  border-color: var(--st-primary-color, #3073ff);
  box-shadow: 0 0 0 1px rgba(48, 115, 255, 0.25);
}
.st-entity-table__checkbox:checked::after {
  opacity: 1;
  transform: scale(1);
}
.st-entity-table__open-btn {
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
.st-entity-table__open-btn:hover {
  box-shadow: 0 1px 3px rgba(49, 51, 63, 0.2);
  background: rgba(49, 51, 63, 0.14);
}
.st-entity-table__open-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
}
.st-entity-table__footer {
  display: flex;
  justify-content: flex-start;
  padding-top: 0.25rem;
}
.st-entity-table__more-btn {
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
.st-entity-table__more-btn:hover {
  background: rgba(48, 115, 255, 0.06);
}
@media (max-width: 640px) {
  .st-entity-table__toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .st-entity-table__toolbar-right {
    justify-content: flex-end;
  }
}
""".strip()

_COMPONENT_JS = """
const template = document.createElement("template");
template.innerHTML = `
<div class="st-entity-table" data-root>
  <div class="st-entity-table__toolbar" data-toolbar>
    <div class="st-entity-table__toolbar-left">
      <span class="st-entity-table__selection" data-selection-text></span>
    </div>
    <div class="st-entity-table__toolbar-right">
      <button type="button" class="st-entity-table__toolbar-btn st-entity-table__toolbar-btn--danger" data-action-delete>
        Delete
      </button>
    </div>
  </div>
  <div class="st-entity-table__table-wrapper">
    <table class="st-entity-table__table" data-table></table>
  </div>
  <div class="st-entity-table__footer" data-footer>
    <button type="button" class="st-entity-table__more-btn" data-action-more>
      Show more
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
  return columns.map((col, index) => ({
    key: col?.key ?? String(index),
    label: col?.label ?? String(col?.key ?? index + 1),
    align: col?.align === "center" || col?.align === "right" ? col.align : "left",
    width: typeof col?.width === "string" ? col.width : null,
  }));
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

const updateToolbar = (toolbarEl, selectionTextEl, deleteButton, selectedIds) => {
  const count = selectedIds.size;
  if (!toolbarEl) {
    return;
  }
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

const renderTable = ({
  tableEl,
  footerEl,
  rows,
  columns,
  page,
  pageSize,
  selectedIds,
  onSelectionChange,
  setStateValue,
  setTriggerValue,
}) => {
  if (!tableEl) {
    return;
  }

  const currentPage = Number.isInteger(page) && page >= 0 ? page : 0;
  const size = Number.isInteger(pageSize) && pageSize > 0 ? pageSize : 100;
  const visibleCount = (currentPage + 1) * size;
  const visibleRows = rows.slice(0, visibleCount);
  const hasMore = rows.length > visibleRows.length;

  tableEl.innerHTML = "";

  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  headerRow.className = "st-entity-table__table-row";

  const selectAllTh = document.createElement("th");
  selectAllTh.className = "st-entity-table__cell--select";
  const selectAllCheckbox = document.createElement("input");
  selectAllCheckbox.type = "checkbox";
  selectAllCheckbox.className =
    "st-entity-table__checkbox st-entity-table__checkbox--header";
  const allVisibleSelected =
    visibleRows.length > 0 &&
    visibleRows.every((row) => selectedIds.has(row.id));
  selectAllCheckbox.checked = allVisibleSelected;
  const hasSelection = selectedIds.size > 0;
  if (hasSelection) {
    selectAllCheckbox.classList.add("is-visible");
  } else {
    selectAllCheckbox.classList.remove("is-visible");
  }
  selectAllCheckbox.onclick = (event) => {
    const checked = event.target.checked;
    visibleRows.forEach((row) => {
      if (checked) {
        selectedIds.add(row.id);
      } else {
        selectedIds.delete(row.id);
      }
    });
    if (typeof onSelectionChange === "function") {
      onSelectionChange();
    } else {
      setStateValue("selected_ids", Array.from(selectedIds));
    }
  };
  selectAllTh.appendChild(selectAllCheckbox);
  headerRow.appendChild(selectAllTh);

  const actionsTh = document.createElement("th");
  actionsTh.className = "st-entity-table__cell--actions";
  headerRow.appendChild(actionsTh);

  columns.forEach((col) => {
    const th = document.createElement("th");
    th.textContent = col.label ?? String(col.key);
    if (col.width) {
      th.style.width = col.width;
    }
    headerRow.appendChild(th);
  });

  thead.appendChild(headerRow);
  tableEl.appendChild(thead);

  const tbody = document.createElement("tbody");

  visibleRows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.className = "st-entity-table__table-row";

    const selectTd = document.createElement("td");
    selectTd.className = "st-entity-table__cell--select";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "st-entity-table__checkbox";
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
    selectTd.appendChild(checkbox);
    tr.appendChild(selectTd);

    const actionsTd = document.createElement("td");
    actionsTd.className = "st-entity-table__cell--actions";
    const openBtn = document.createElement("button");
    openBtn.type = "button";
    openBtn.className = "st-entity-table__open-btn";
    openBtn.textContent = "Open";
    openBtn.setAttribute("aria-label", "Open row");
    openBtn.onclick = (event) => {
      event.preventDefault();
      setTriggerValue("open", row.id);
    };
    actionsTd.appendChild(openBtn);
    tr.appendChild(actionsTd);

    columns.forEach((col) => {
      const td = document.createElement("td");
      const raw = row.cells && Object.prototype.hasOwnProperty.call(row.cells, col.key)
        ? row.cells[col.key]
        : "";
      td.textContent = raw == null ? "" : String(raw);
      td.style.textAlign = col.align || "left";
      tr.appendChild(td);
    });

    tbody.appendChild(tr);
  });

  tableEl.appendChild(tbody);

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

export default function(component) {
  const { parentElement, data = {}, setStateValue, setTriggerValue } = component;
  const root = ensureRoot(parentElement);
  if (!root) {
    return;
  }

  const toolbarEl = root.querySelector("[data-toolbar]");
  const selectionTextEl = root.querySelector("[data-selection-text]");
  const deleteButton = root.querySelector("[data-action-delete]");
  const tableEl = root.querySelector("[data-table]");
  const footerEl = root.querySelector("[data-footer]");

  const rows = normalizeRows(data.rows);
  const columns = normalizeColumns(data.columns);
  const pageSize = Number.isInteger(data.pageSize) && data.pageSize > 0 ? data.pageSize : 100;
  const page = Number.isInteger(data.page) && data.page >= 0 ? data.page : 0;
  const selectedIds = new Set(toArray(data.selectedIds));

  const onSelectionChange = () => {
    updateToolbar(toolbarEl, selectionTextEl, deleteButton, selectedIds);
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

  updateToolbar(toolbarEl, selectionTextEl, deleteButton, selectedIds);

  renderTable({
    tableEl,
    footerEl,
    rows,
    columns,
    page,
    pageSize,
    selectedIds,
    onSelectionChange,
    setStateValue,
    setTriggerValue,
  });
}
""".strip()

_entity_table_component = st.components.v2.component(
    "entity_table",
    html=_COMPONENT_HTML,
    css=_COMPONENT_CSS,
    js=_COMPONENT_JS,
)


def _format_cell_value(value: Any, column: ColumnDefinition) -> str:
    """Приводит значение ячейки к строке с учётом опций колонки."""
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
        align = column.get("align") or "left"
        width = column.get("width")
        normalized.append(
            {
                "key": str(col_key),
                "label": str(label),
                "align": align if align in {"left", "center", "right"} else "left",
                "width": str(width) if isinstance(width, str) else None,
                "field": field,
                "compute": column.get("compute"),
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


def render_entity_table(
    *,
    entity_name: EntityName,
    key: str,
    rows: Sequence[Dict[str, Any]],
    columns: Sequence[ColumnDefinition],
    id_field: str = "id",
    empty_message: str = "No data to display.",
    page_size: int = 100,
    on_open: Optional[Callable[[Dict[str, Any]], None]] = None,
    on_delete: Optional[Callable[[List[Any]], None]] = None,
) -> None:
    """Отрисовывает универсальную таблицу сущностей и обрабатывает действия."""
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
    raw_page = (
        component_state.get("page")
        if isinstance(component_state, dict)
        else 0
    )
    initial_page = int(raw_page) if isinstance(
        raw_page, int) and raw_page >= 0 else 0

    normalized_columns, _ = _normalize_columns(columns)
    rows_payload, id_to_row = _build_rows_payload(
        rows=rows,
        id_field=id_field,
        columns=normalized_columns,
    )

    callbacks: Dict[str, Callable[[], None]] = {
        "on_selected_ids_change": lambda: None,
        "on_open_change": lambda: None,
        "on_delete_change": lambda: None,
        "on_page_change": lambda: None,
    }

    result = _entity_table_component(
        key=key,
        data={
            "rows": rows_payload,
            "columns": [
                {
                    "key": col["key"],
                    "label": col["label"],
                    "align": col["align"],
                    "width": col["width"],
                }
                for col in normalized_columns
            ],
            "pageSize": max(1, int(page_size)),
            "page": initial_page,
            "selectedIds": initial_selected,
        },
        default={
            "selected_ids": initial_selected,
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

    if (
        on_delete is not None
        and isinstance(delete_ids, list)
        and delete_ids
    ):
        on_delete(delete_ids)

    handle_selection_change(entity_name, selected_ids)


__all__ = ["render_entity_table", "ColumnDefinition"]
