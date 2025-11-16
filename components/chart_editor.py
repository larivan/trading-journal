"""Переиспользуемые UI-хелперы для работы с чартами и их привязками."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

import streamlit as st

from db import add_chart, delete_chart, update_chart

ChartRow = Dict[str, Any]


def chart_editor_value_state_key(widget_key: str) -> str:
    """Возвращает ключ session_state для хранения данных редактора."""
    return f"{widget_key}__value"


def _layout_from_columns(columns: int) -> str:
    if columns >= 3:
        return "grid3"
    if columns == 2:
        return "grid2"
    return "column"


def _sanitize_chart_rows(
    rows: Sequence[ChartRow],
    *,
    keep_empty: bool = False,
) -> List[ChartRow]:
    sanitized: List[ChartRow] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        chart_url = str(row.get("chart_url") or "").strip()
        cleaned = {
            "id": row.get("id"),
            "chart_url": chart_url,
            "caption": (row.get("caption") or "").strip(),
        }
        if chart_url or keep_empty:
            sanitized.append(cleaned)
    return sanitized


_COMPONENT_HTML = """
<div class="st-chart-editor" data-root>
  <div class="st-chart-editor__body">
    <div class="st-chart-editor__empty" data-empty>Добавьте первый чарт, чтобы увидеть превью.</div>
    <div class="st-chart-editor__cards" data-cards></div>
  </div>
  <div class="st-chart-editor__form">
    <div class="st-chart-editor__inputs">
      <label class="st-chart-editor__field">
        <span>Image link</span>
        <input type="url" data-input-url placeholder="https://example.com/chart.png" />
      </label>
      <label class="st-chart-editor__field">
        <span>Caption</span>
        <input type="text" data-input-caption placeholder="Optional note" />
      </label>
      <button type="button" class="st-chart-editor__add" data-add>Добавить</button>
    </div>
    <div class="st-chart-editor__error" data-error></div>
  </div>
</div>
""".strip()

_COMPONENT_CSS = """
:host {
  width: 100%;
}
.st-chart-editor {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
}
.st-chart-editor__form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.85rem;
  border: 1px solid var(--st-secondary-background-color);
  border-radius: 0.75rem;
  background: var(--st-secondary-background-color);
}
.st-chart-editor__inputs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.st-chart-editor__field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1 1 220px;
  font-size: 0.85rem;
  color: var(--st-color-text-light, rgba(49, 51, 63, 0.6));
}
.st-chart-editor__field input {
  width: 100%;
  appearance: none;
  border-radius: 0.5rem;
  border: 1px solid transparent;
  padding: 0.5rem 0.5rem;
  font-size: 0.95rem;
  background: #fff;
  transition: border-color 120ms ease, background 120ms ease;
  box-sizing: border-box;
}
.st-chart-editor__field input:focus {
  border-color: var(--st-primary-color);
  outline: none;
  background: rgba(48, 115, 255, 0.08);
}
.st-chart-editor__add {
  align-self: flex-end;
  margin-left: auto;
  appearance: none;
  border: none;
  border-radius: 0.5rem;
  padding: 0.55rem 1.5rem;
  background: var(--st-primary-color);
  color: #fff;
  cursor: pointer;
  transition: opacity 120ms ease;
}
.st-chart-editor__add:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.st-chart-editor__error {
  font-size: 0.85rem;
  color: #e03131;
  display: none;
}
.st-chart-editor__body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.st-chart-editor__empty {
  border: 2px dashed rgba(49, 51, 63, 0.15);
  border-radius: 0.85rem;
  padding: 1.75rem;
  text-align: center;
  color: var(--st-color-text-light, rgba(49, 51, 63, 0.6));
  font-size: 0.95rem;
}
.st-chart-editor__cards {
  display: grid;
  gap: 1.4rem;
  width: 100%;
}
.st-chart-editor__cards[data-layout="column"] {
  grid-template-columns: minmax(0, 1fr);
}
.st-chart-editor__cards[data-layout="grid2"] {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.st-chart-editor__cards[data-layout="grid3"] {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
@media (max-width: 900px) {
  .st-chart-editor__cards[data-layout="grid3"] {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .st-chart-editor__cards[data-layout="grid2"],
  .st-chart-editor__cards[data-layout="grid3"] {
    grid-template-columns: minmax(0, 1fr);
  }
}
.st-chart-card {
  position: relative;
  border-radius: 0.9rem;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}
.st-chart-card__remove {
  position: absolute;
  top: -8px;
  right: -8px;
  z-index: 1;
}
.st-chart-card__image {
  position: relative;
  overflow: hidden;
  border-radius: 0.65rem;
  border: 1px solid rgba(49, 51, 63, 0.08);
  background: #fff;
  min-height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(49, 51, 63, 0.08);
}
.st-chart-card__image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.st-chart-card__caption {
  text-align: center;
  font-size: 0.9rem;
  color: var(--st-color-text, #1c1c1c);
  cursor: text;
  transition: color 120ms ease;
  min-height: 1.5rem;
}
.st-chart-card__caption.is-placeholder {
  color: var(--st-color-text-light, rgba(49, 51, 63, 0.6));
  font-style: italic;
  font-weight: 500;
}
.st-chart-card__caption-input {
  width: 100%;
  border: none;
  border-bottom: 1px solid var(--st-primary-color);
  background: transparent;
  font-size: 0.9rem;
  padding: 0.2rem 0.25rem;
  text-align: center;
  color: var(--st-color-text, #1c1c1c);
}
.st-chart-card__caption-input:focus {
  outline: none;
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
  transition: background 120ms ease, color 120ms ease;
}
.st-vtabs__remove:hover {
  background: #cccccc;
  color: #000;
}
""".strip()

_COMPONENT_JS = """
const template = document.createElement("template");
template.innerHTML = `
<div class="st-chart-editor" data-root>
  <div class="st-chart-editor__body">
    <div class="st-chart-editor__empty" data-empty>Добавьте первый чарт, чтобы увидеть превью.</div>
    <div class="st-chart-editor__cards" data-cards></div>
  </div>
  <div class="st-chart-editor__form">
    <div class="st-chart-editor__inputs">
      <label class="st-chart-editor__field">
        <span>Image link</span>
        <input type="url" data-input-url placeholder="https://example.com/chart.png" />
      </label>
      <label class="st-chart-editor__field">
        <span>Caption</span>
        <input type="text" data-input-caption placeholder="Optional note" />
      </label>
      <button type="button" class="st-chart-editor__add" data-add>Добавить</button>
    </div>
    <div class="st-chart-editor__error" data-error></div>
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

const normalizeCharts = (charts) => {
  if (!Array.isArray(charts)) {
    return [];
  }
  return charts
    .map((chart) => ({
      id: chart?.id ?? null,
      chart_url: typeof chart?.chart_url === "string" ? chart.chart_url : "",
      caption: typeof chart?.caption === "string" ? chart.caption : "",
    }))
    .filter((chart) => String(chart.chart_url || "").trim() !== "");
};

const CAPTION_PLACEHOLDER = "Дважды кликните, чтобы добавить подпись";

const renderCards = (cardsEl, charts, { onChange, onRemove }) => {
  cardsEl.innerHTML = "";
  charts.forEach((chart, index) => {
    const card = document.createElement("div");
    card.className = "st-chart-card";

    const remove = document.createElement("button");
    remove.className = "st-vtabs__remove st-chart-card__remove";
    remove.type = "button";
    remove.textContent = "×";
    remove.onclick = (event) => {
      event.preventDefault();
      onRemove(index);
    };

    const imageWrapper = document.createElement("div");
    imageWrapper.className = "st-chart-card__image";
    const image = document.createElement("img");
    image.alt = chart.caption || "Chart";
    image.src = chart.chart_url;
    imageWrapper.appendChild(image);

    const caption = document.createElement("div");
    caption.className = "st-chart-card__caption";

    const applyCaptionValue = (value) => {
      const nextValue = (value || "").trim();
      if (nextValue) {
        caption.textContent = nextValue;
        caption.classList.remove("is-placeholder");
      } else {
        caption.textContent = CAPTION_PLACEHOLDER;
        caption.classList.add("is-placeholder");
      }
    };

    const activateCaptionEdit = () => {
      if (caption.dataset.editing === "true") {
        return;
      }
      caption.dataset.editing = "true";
      caption.classList.remove("is-placeholder");
      caption.innerHTML = "";
      const input = document.createElement("input");
      input.type = "text";
      input.value = chart.caption || "";
      input.placeholder = "Подпись";
      input.className = "st-chart-card__caption-input";
      caption.appendChild(input);
      input.focus();
      input.select();

      const finish = (commit) => {
        if (caption.dataset.editing !== "true") {
          return;
        }
        caption.dataset.editing = "false";
        const nextValue = commit ? input.value : chart.caption || "";
        caption.innerHTML = "";
        applyCaptionValue(nextValue);
        if (commit) {
          onChange(index, { caption: nextValue });
        }
      };

      input.onblur = () => finish(true);
      input.onkeydown = (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          finish(true);
        } else if (event.key === "Escape") {
          event.preventDefault();
          finish(false);
        }
      };
    };

    caption.ondblclick = (event) => {
      event.preventDefault();
      activateCaptionEdit();
    };

    applyCaptionValue(chart.caption || "");

    card.appendChild(remove);
    card.appendChild(imageWrapper);
    card.appendChild(caption);
    cardsEl.appendChild(card);
  });
};

export default function(component) {
  const { parentElement, data = {}, setStateValue } = component;
  const root = ensureRoot(parentElement);
  if (!root) {
    return;
  }

  const urlInput = root.querySelector("[data-input-url]");
  const captionInput = root.querySelector("[data-input-caption]");
  const addButton = root.querySelector("[data-add]");
  const cardsEl = root.querySelector("[data-cards]");
  const emptyEl = root.querySelector("[data-empty]");
  const errorEl = root.querySelector("[data-error]");
  let currentCharts = normalizeCharts(data.charts);
  const currentLayout = ["grid2", "grid3"].includes(data.layout) ? data.layout : "column";
  cardsEl.dataset.layout = currentLayout;

  const showError = (message) => {
    const text = message || "";
    errorEl.textContent = text;
    errorEl.style.display = text ? "block" : "none";
  };

  const refreshCards = () => {
    renderCards(cardsEl, currentCharts, {
      onChange: updateChart,
      onRemove: removeChart,
    });
    emptyEl.style.display = currentCharts.length ? "none" : "flex";
  };

  const commitCharts = (nextCharts, emit = true) => {
    currentCharts = nextCharts;
    refreshCards();
    if (emit) {
      setStateValue("charts", currentCharts);
    }
  };

  const updateChart = (index, payload) => {
    const next = currentCharts.map((chart, idx) =>
      idx === index ? { ...chart, ...payload } : chart
    );
    commitCharts(next);
  };

  const removeChart = (index) => {
    const next = currentCharts.filter((_, idx) => idx !== index);
    commitCharts(next);
  };

  const addChart = () => {
    const url = urlInput.value.trim();
    const caption = captionInput.value.trim();
    if (!url) {
      showError("Вставьте ссылку на изображение.");
      return;
    }
    if (!/^https?:\\/\\//i.test(url)) {
      showError("Ссылка должна начинаться с http(s).");
      return;
    }
    showError("");
    const next = [
      ...currentCharts,
      {
        id: null,
        chart_url: url,
        caption,
      },
    ];
    urlInput.value = "";
    captionInput.value = "";
    commitCharts(next);
  };

  addButton.onclick = (event) => {
    event.preventDefault();
    addChart();
  };

  urlInput.onkeydown = (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      addChart();
    }
  };
  captionInput.onkeydown = (event) => {
    if (event.key === "Enter" && urlInput.value.trim()) {
      event.preventDefault();
      addChart();
    }
  };

  refreshCards();
}
""".strip()

_chart_editor_component = st.components.v2.component(
    "chart_editor",
    html=_COMPONENT_HTML,
    css=_COMPONENT_CSS,
    js=_COMPONENT_JS,
)


def render_chart_editor(
    *,
    key: str,
    base_rows: Sequence[ChartRow],
    title: str = "Charts",
    caption: Optional[str] = "Paste links to your TradingView snapshots so they stay linked to this record.",
    layout_columns: int = 1,
) -> List[ChartRow]:
    """Отрисовывает универсальный редактор чартов и возвращает его значение."""
    sanitized_rows = _sanitize_chart_rows(base_rows)
    if title:
        st.subheader(title)
    if caption:
        st.caption(caption)

    layout_mode = _layout_from_columns(layout_columns)
    value_state_key = chart_editor_value_state_key(key)

    callbacks = {
        "on_charts_change": lambda: None,
    }

    result = _chart_editor_component(
        key=key,
        data={
            "charts": sanitized_rows,
            "layout": layout_mode,
        },
        default={"charts": sanitized_rows},
        **callbacks,
    )

    charts_value = result.get("charts") if isinstance(result, dict) else None
    if isinstance(charts_value, list):
        sanitized_value = _sanitize_chart_rows(charts_value, keep_empty=True)
        st.session_state[value_state_key] = sanitized_value
        return sanitized_value

    cached_value = st.session_state.get(value_state_key)
    if isinstance(cached_value, list):
        sanitized_cached = _sanitize_chart_rows(cached_value, keep_empty=True)
        st.session_state[value_state_key] = sanitized_cached
        return sanitized_cached

    st.session_state[value_state_key] = sanitized_rows
    return sanitized_rows


def chart_table_rows(charts: List[ChartRow]) -> List[ChartRow]:
    """Готовит строки чарта для редактора."""
    return [
        {
            "id": chart.get("id"),
            "chart_url": chart.get("chart_url") or "",
            "caption": chart.get("caption") or "",
        }
        for chart in charts
    ]


def normalize_editor_rows(editor_value: Any) -> List[ChartRow]:
    """Приводит ответ data_editor к списку словарей."""
    if isinstance(editor_value, list):
        raw_rows = editor_value
    elif hasattr(editor_value, "to_dict"):
        raw_rows = editor_value.to_dict("records")  # type: ignore[call-arg]
    else:
        raw_rows = []

    normalized: List[ChartRow] = []
    for row in raw_rows:
        chart_url = (row.get("chart_url") or "").strip()
        normalized.append({
            "id": row.get("id"),
            "chart_url": chart_url,
            "caption": row.get("caption") or "",
        })
    return normalized


def persist_chart_editor(
    *,
    attached_charts: List[ChartRow],
    editor_rows: List[ChartRow],
    attach_chart: Callable[[int], None],
) -> None:
    """Синхронизирует таблицу чартов с данными из редактора."""
    desired_rows: List[ChartRow] = []
    for row in editor_rows:
        chart_url = (row.get("chart_url") or "").strip()
        if not chart_url:
            continue
        desired_rows.append({
            "id": _clean_chart_id(row.get("id")),
            "chart_url": chart_url,
            "caption": (row.get("caption") or "").strip() or None,
        })

    current_by_id = {chart["id"]: chart for chart in attached_charts}
    desired_ids = {row["id"] for row in desired_rows if row["id"] is not None}

    for chart_id in set(current_by_id.keys()) - desired_ids:
        if chart_id is not None:
            delete_chart(chart_id)

    for row in desired_rows:
        chart_id = row.get("id")
        if chart_id is None or chart_id not in current_by_id:
            continue
        existing = current_by_id[chart_id]
        existing_url = (existing.get("chart_url") or "").strip()
        existing_caption = (existing.get("caption") or None)
        if row["chart_url"] != existing_url or row["caption"] != existing_caption:
            update_chart(chart_id, row["chart_url"], row["caption"])

    for row in desired_rows:
        if row.get("id") is not None:
            continue
        chart_id = add_chart(row["chart_url"], row["caption"])
        # Внешняя функция решает, к какой сущности привязать чарт.
        attach_chart(chart_id)


def _clean_chart_id(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
