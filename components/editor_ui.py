"""Общие UI-компоненты для редакторов (trade_editor, analysis_editor)."""

from typing import Callable, Dict, List, Optional

import streamlit as st

from utils.cached_data import invalidate_notes


def section_divider() -> None:
    st.markdown(
        "<hr style='margin:6px 0;border:0;border-top:1px solid rgba(49,51,63,.1)'>",
        unsafe_allow_html=True,
    )


def render_delete_dialog(
    pending_key: str,
    entity_label: str,
    delete_fn: Callable,
    user_id: int,
    redirect_page: str,
    invalidate_fn: Optional[Callable] = None,
) -> None:
    """Отображает диалог подтверждения удаления сущности.

    pending_key — ключ session_state с id сущности (например "_ae_pending_delete").
    entity_label — название для заголовка ("analysis" / "trade").
    delete_fn — функция удаления, принимает (entity_id, user_id).
    redirect_page — страница для перехода после удаления.
    """
    if not st.session_state.get(pending_key):
        return

    @st.dialog(f"Delete {entity_label}")
    def _confirm() -> None:
        st.warning(f"Delete this {entity_label}? This cannot be undone.")
        c1, c2 = st.columns(2)
        if c1.button("Delete", type="primary", width="stretch"):
            try:
                delete_fn(st.session_state[pending_key], user_id)
            except Exception as exc:
                st.toast(f"Failed to delete: {exc}", icon="❌")
            st.session_state.pop(pending_key, None)
            (invalidate_fn or st.cache_data.clear)()
            st.switch_page(redirect_page)
        if c2.button("Cancel", width="stretch"):
            st.session_state.pop(pending_key, None)
            st.rerun()

    _confirm()


def render_editor_actions(
    is_new: bool,
    pending_delete_key: str,
    entity_id: Optional[int],
    default_back_page: str,
) -> bool:
    """Отрисовывает строку кнопок: ← Back | Save | Delete.

    Возвращает True, если нажата кнопка Save.
    """
    show_delete = not is_new and entity_id is not None
    cols = st.columns(3 if show_delete else 2)

    if cols[0].button("← Back", width="stretch"):
        back_page = st.session_state.pop("_back_page", default_back_page)
        back_params = st.session_state.pop("_back_params", {})
        if back_params:
            st.session_state["_returning_params"] = back_params
        st.switch_page(back_page)

    submitted = cols[1].button("Save", type="primary", width="stretch")

    if show_delete:
        if cols[2].button("Delete", type="secondary", width="stretch"):
            st.session_state[pending_delete_key] = entity_id
            st.rerun()

    return submitted


def render_entry_card(
    entry_id: int,
    badge: str,
    time_display: str,
    body: str,
    images: List[Dict],
    on_save: Callable[[str], None],
    on_delete: Callable[[], None],
    delete_help: str = "Delete",
    key_prefix: str = "entry",
) -> None:
    """Карточка записи (stage / note) с кнопками ред./удал. и inline-редактированием.

    entry_id — уникальный id записи.
    badge — текст в [квадратных скобках] заголовка (например "[Pre-Market]").
    time_display — строка времени (например "09:30").
    body — тело записи.
    images — список {"image_url": ...} для показа под телом.
    on_save — вызывается с новым телом при сохранении.
    on_delete — вызывается при нажатии удалить.
    delete_help — tooltip кнопки удаления.
    key_prefix — префикс для уникальности ключей виджетов.
    """
    _edit_key = f"_editing_{key_prefix}_{entry_id}"

    with st.container(border=True):
        hdr_col, actions_col = st.columns([0.85, 0.15])
        hdr_col.markdown(f"**{badge}** {time_display}")

        edit_col, del_col = actions_col.columns(2, gap="small")
        if edit_col.button("✎", key=f"_edit_btn_{key_prefix}_{entry_id}", help="Edit", use_container_width=True):
            st.session_state[_edit_key] = not st.session_state.get(_edit_key, False)
            st.rerun()
        if del_col.button("✕", key=f"_del_{key_prefix}_{entry_id}", help=delete_help, use_container_width=True):
            on_delete()
            invalidate_notes()
            st.rerun()

        if st.session_state.get(_edit_key):
            new_body = st.text_area(
                "",
                value=body,
                key=f"_edit_area_{key_prefix}_{entry_id}",
                label_visibility="collapsed",
            )
            save_col, cancel_col, _ = st.columns([0.12, 0.12, 0.76])
            if save_col.button("Save", key=f"_edit_save_{key_prefix}_{entry_id}", type="primary", width="stretch"):
                on_save(new_body)
                st.session_state.pop(_edit_key, None)
                invalidate_notes()
                st.rerun()
            if cancel_col.button("Cancel", key=f"_edit_cancel_{key_prefix}_{entry_id}", width="stretch"):
                st.session_state.pop(_edit_key, None)
                st.rerun()
        else:
            if body and body != "(image)":
                st.markdown(body)

        if images:
            img_cols = st.columns(min(len(images), 2))
            for i, img in enumerate(images):
                img_cols[i % 2].image(img["image_url"], use_container_width=True)
