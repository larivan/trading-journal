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
