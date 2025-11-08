import streamlit as st

from components.trade_forms import render_trade_form
from components.trade_manager import render_trade_manager
from db import create_trade, delete_trade, get_trade_by_id


def set_dialog_flag(flag: str, value: bool) -> None:
    """Удобная обёртка для включения/отключения конкретного диалога."""
    st.session_state[flag] = value


@st.dialog("Создание сделки")
def create_trade_dialog() -> None:
    """Модалка создания: собирает данные формы и пишет их в базу."""
    account_options = st.session_state.get("account_options_for_forms", {})
    form_data = render_trade_form(
        account_options,
        form_key="create_trade_form",
        submit_label="Создать",
    )
    if st.button("Отмена", key="create_trade_cancel", use_container_width=True):
        set_dialog_flag("show_create_trade", False)
        st.rerun()
    if not form_data:
        return
    try:
        create_trade(form_data)
        st.success("Сделка создана.")
        set_dialog_flag("show_create_trade", False)
        st.rerun()
    except Exception as exc:  # pragma: no cover - UI feedback
        st.error(f"Не удалось создать сделку: {exc}")


@st.dialog("Редактирование сделки", width="large")
def edit_trade_dialog() -> None:
    """Модалка редактирования выбранной сделки."""
    trade_id = st.session_state.get("selected_trade_id")
    if not trade_id:
        st.info("Сделка не выбрана.")
        return
    trade = get_trade_by_id(trade_id)
    if not trade:
        st.error("Сделка не найдена.")
        return
    render_trade_manager(trade)
    if st.button("Отмена", key="edit_trade_cancel", use_container_width=True):
        set_dialog_flag("show_edit_trade", False)
        st.rerun()


@st.dialog("Удаление сделки")
def delete_trade_dialog() -> None:
    """Модалка удаления с подтверждением и сбросом выбранной строки."""
    trade_id = st.session_state.get("selected_trade_id")
    if not trade_id:
        st.info("Сделка не выбрана.")
        return
    st.warning(
        "Сделка будет удалена безвозвратно. Подтвердите действие.",
        icon="⚠️",
    )
    col_ok, col_cancel = st.columns(2)
    confirm = col_ok.button(
        "Удалить",
        type="primary",
        use_container_width=True,
    )
    cancel = col_cancel.button(
        "Отмена",
        use_container_width=True,
    )
    if confirm:
        try:
            delete_trade(trade_id)
            st.success("Сделка удалена.")
            set_dialog_flag("show_delete_trade", False)
            st.session_state["selected_trade_id"] = None
            st.rerun()
        except Exception as exc:  # pragma: no cover
            st.error(f"Не удалось удалить сделку: {exc}")
    if cancel:
        set_dialog_flag("show_delete_trade", False)
        st.rerun()
