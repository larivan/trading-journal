const template = document.createElement("template");
template.innerHTML = `
<div class="st-chart-editor" data-root>
  <div class="st-chart-editor__body">
    <div class="st-chart-editor__empty" data-empty>Добавьте первое изображение, чтобы увидеть превью.</div>
    <div class="st-chart-editor__cards" data-cards></div>
  </div>
  <div class="st-chart-editor__form">
    <div class="st-chart-editor__inputs">
      <input class="st-chart-editor__field" type="url" data-input-url placeholder="Image link" />
      <input class="st-chart-editor__field" type="text" data-input-caption placeholder="Caption" />
      <button type="button" class="st-chart-editor__add" data-add>Add</button>
    </div>
    <div class="st-chart-editor__error" data-error></div>
  </div>
</div>
`;

const FS_LIGHTBOX_SRC = "https://cdn.jsdelivr.net/npm/fslightbox/index.js";
let fsLightboxPromise = null;

const loadFsLightbox = () => {
  if (typeof window !== "undefined" && typeof window.refreshFsLightbox === "function") {
    return Promise.resolve();
  }
  if (fsLightboxPromise) {
    return fsLightboxPromise;
  }
  fsLightboxPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${FS_LIGHTBOX_SRC}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("FsLightbox failed to load")), {
        once: true,
      });
      return;
    }
    const script = document.createElement("script");
    script.src = FS_LIGHTBOX_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("FsLightbox failed to load"));
    document.head.appendChild(script);
  }).catch((error) => {
    console.error(error);
  });
  return fsLightboxPromise;
};

const ensureFsLightboxReady = () =>
  loadFsLightbox().then(() => {
    if (typeof window !== "undefined" && typeof window.refreshFsLightbox === "function") {
      window.refreshFsLightbox();
    }
  });

const openLightboxLink = (link) =>
  ensureFsLightboxReady().then(() => {
    if (!link) {
      return;
    }
    const event = new MouseEvent("click", {
      bubbles: true,
      cancelable: true,
      view: window,
    });
    link.dispatchEvent(event);
  });

const ensureGalleryId = (element) => {
  if (!element.dataset.galleryId) {
    element.dataset.galleryId = `chart-gallery-${Math.random().toString(36).slice(2)}`;
  }
  return element.dataset.galleryId;
};

const ensureLightboxPortal = () => {
  const attr = "data-chart-editor-lightbox-portal";
  let portal = document.querySelector(`[${attr}]`);
  if (!portal) {
    portal = document.createElement("div");
    portal.setAttribute(attr, "true");
    portal.style.position = "fixed";
    portal.style.top = "-9999px";
    portal.style.left = "-9999px";
    portal.style.width = "0";
    portal.style.height = "0";
    portal.style.overflow = "hidden";
    document.body.appendChild(portal);
  }
  return portal;
};

const syncLightboxLinks = (galleryId, images) => {
  const portal = ensureLightboxPortal();
  const selector = `[data-chart-editor-gallery="${galleryId}"]`;
  portal.querySelectorAll(selector).forEach((node) => node.remove());
  return images.map((image) => {
    const link = document.createElement("a");
    link.href = image.image_url;
    link.dataset.fslightbox = galleryId;
    link.dataset.chartEditorGallery = galleryId;
    link.dataset.type = "image";
    link.dataset.caption = (image.caption || "").trim();
    link.setAttribute("aria-hidden", "true");
    link.tabIndex = -1;
    portal.appendChild(link);
    return link;
  });
};

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

const normalizeImages = (images) => {
  if (!Array.isArray(images)) {
    return [];
  }
  return images
    .map((image) => ({
      id: image?.id ?? null,
      image_url: typeof image?.image_url === "string" ? image.image_url : "",
      caption: typeof image?.caption === "string" ? image.caption : "",
    }))
    .filter((image) => String(image.image_url || "").trim() !== "");
};

const CAPTION_PLACEHOLDER = "Дважды кликните, чтобы добавить подпись";

const renderCards = (cardsEl, images, { onChange, onRemove }) => {
  const galleryId = ensureGalleryId(cardsEl);
  const portalLinks = syncLightboxLinks(galleryId, images);
  cardsEl.innerHTML = "";
  if (!images.length) {
    cardsEl.style.display = "none";
    return;
  }
  cardsEl.style.display = "grid";
  images.forEach((image, index) => {
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

    const portalLink = portalLinks[index];

    const imageWrapper = document.createElement("div");
    imageWrapper.className = "st-chart-card__image";
    const img = document.createElement("img");
    img.alt = image.caption || "Image";
    img.src = image.image_url;
    imageWrapper.appendChild(img);
    imageWrapper.ondblclick = (event) => {
      event.preventDefault();
      openLightboxLink(portalLink);
    };

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
      input.value = image.caption || "";
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
        const nextValue = commit ? input.value : image.caption || "";
        caption.innerHTML = "";
        applyCaptionValue(nextValue);
        if (commit) {
          onChange(index, { caption: nextValue });
        }
      };

      input.onblur = () => finish(true);
      input.onkeydown = (event) => {
        event.stopPropagation();
        event.stopImmediatePropagation();
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

    applyCaptionValue(image.caption || "");

    card.appendChild(remove);
    card.appendChild(imageWrapper);
    card.appendChild(caption);
    cardsEl.appendChild(card);
  });
  ensureFsLightboxReady();
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
  let currentImages = normalizeImages(data.charts);
  const currentLayout = ["grid2", "grid3"].includes(data.layout) ? data.layout : "column";
  cardsEl.dataset.layout = currentLayout;

  const showError = (message) => {
    const text = message || "";
    errorEl.textContent = text;
    errorEl.style.display = text ? "block" : "none";
  };

  const refreshCards = () => {
    renderCards(cardsEl, currentImages, {
      onChange: updateImage,
      onRemove: removeImage,
    });
    emptyEl.style.display = currentImages.length ? "none" : "flex";
  };

  const commitImages = (nextImages, emit = true) => {
    currentImages = nextImages;
    refreshCards();
    if (emit) {
      setStateValue("charts", currentImages);
    }
  };

  const updateImage = (index, payload) => {
    const next = currentImages.map((image, idx) =>
      idx === index ? { ...image, ...payload } : image
    );
    commitImages(next);
  };

  const removeImage = (index) => {
    const next = currentImages.filter((_, idx) => idx !== index);
    commitImages(next);
  };

  const sanitizeUrl = () => {
    const value = urlInput.value.trim();
    if (value && !/^https?:\/\//i.test(value)) {
      urlInput.value = "";
    }
  };

  urlInput.oninput = sanitizeUrl;

  const addImage = () => {
    sanitizeUrl();
    const url = urlInput.value.trim();
    const caption = captionInput.value.trim();
    if (!url) {
      return;
    }
    const next = [
      ...currentImages,
      {
        id: null,
        image_url: url,
        caption,
      },
    ];
    urlInput.value = "";
    captionInput.value = "";
    commitImages(next);
  };

  addButton.onclick = (event) => {
    event.preventDefault();
    addImage();
  };

  urlInput.onkeydown = (event) => {
    event.stopPropagation();
    event.stopImmediatePropagation();
    if (event.key === "Enter") {
      event.preventDefault();
      addImage();
    }
  };
  captionInput.onkeydown = (event) => {
    event.stopPropagation();
    event.stopImmediatePropagation();
    if (event.key === "Enter" && urlInput.value.trim()) {
      event.preventDefault();
      addImage();
    }
  };

  refreshCards();
}
