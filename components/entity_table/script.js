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
