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
  const excerptLimit = Number(data.excerpt_limit) || 120;
  let selected = new Set();
  let _eventCounter = 0;

  const emitEvent = (payload) => {
    setStateValue("event", { ...payload, event_id: ++_eventCounter });
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
      const excerpt = document.createElement("div");
      excerpt.className = "ns-excerpt";
      excerpt.textContent = note.excerpt || "";
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
        return (note.excerpt || "").toLowerCase().includes(q);
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
        const excerpt = document.createElement("div");
        excerpt.className = "ns-browse-item__excerpt";
        excerpt.textContent = note.excerpt || "";
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
