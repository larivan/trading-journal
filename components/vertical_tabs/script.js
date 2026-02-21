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
