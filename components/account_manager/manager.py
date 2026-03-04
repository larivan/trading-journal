"""Диалог создания и редактирования аккаунтов."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, Optional

import streamlit as st

from config import (
    ACCOUNT_DIALOG_NAME,
    ACCOUNT_ID_STATE,
    ACCOUNT_MANAGER_KEY_PREFIX,
    ACCOUNT_SUCCESS_STATE,
)
from db import (
    create_account,
    delete_account,
    get_account,
    set_account_archived,
    update_account,
)
from utils.auth import get_current_user_id
from utils.session_state import close_dialog, dialog_is_active


def render_account_manager() -> None:
    """Рендерит диалог для создания, архивации и удаления аккаунтов."""
    if ACCOUNT_SUCCESS_STATE in st.session_state:
        st.toast(st.session_state.pop(ACCOUNT_SUCCESS_STATE), icon="🔥")

    if not dialog_is_active(ACCOUNT_DIALOG_NAME):
        return

    user_id = get_current_user_id()
    account_id = st.session_state.get(ACCOUNT_ID_STATE)
    is_new = account_id is None
    account: Dict[str, Any] = {}

    if not is_new:
        account = get_account(int(account_id), user_id) or {}
        if not account:
            st.error("Account not found.")
            st.session_state.pop(ACCOUNT_ID_STATE, None)
            close_dialog()
            st.rerun()
            return

    state_key = f"{ACCOUNT_MANAGER_KEY_PREFIX}{account_id or 'new'}"

    @st.dialog(
        _get_dialog_title(account, is_new),
        width="small",
        on_dismiss=_handle_dialog_dismiss,
    )
    def _dialog() -> None:
        if is_new:
            name_value = st.text_input(
                "Name",
                value=account.get("name") or "",
                key=f"{state_key}_name",
                placeholder="Account name",
            )
            broker_value = st.text_input(
                "Broker",
                value=account.get("broker") or "",
                key=f"{state_key}_broker",
                placeholder="Optional",
            )
            balance_value = st.number_input(
                "Starting balance",
                value=float(account.get("starting_balance") or 0.0),
                key=f"{state_key}_starting_balance",
                step=0.1,
            )
            is_prop_value = st.checkbox(
                "Prop account",
                value=bool(account.get("is_prop")),
                key=f"{state_key}_is_prop",
            )
        else:
            if bool(account.get("is_prop")) or bool(account.get("archived")):
                st.markdown(
                    f"""{':blue-badge[Prop Account]' if bool(account.get("is_prop")) else ''}
                    {':gray-badge[Archived]' if bool(account.get("archived")) else ''}"""
                )
            st.markdown(f"**Broker:** {account.get('broker') or 'N/A'}")
            st.markdown(
                f"**Starting balance:** ${float(account.get('starting_balance') or 0.0):,.2f}"
            )

        archived = bool(account.get("archived"))
        c1, c2, c3 = st.columns(3)
        save_clicked = c1.button(
            "Save",
            type="primary",
            width="stretch",
            key=f"{state_key}_save",
            disabled=not is_new,
        )
        archive_clicked = c2.button(
            "Restore" if archived else "Archive",
            type="secondary",
            width="stretch",
            key=f"{state_key}_archive",
            help="Archived accounts stay in the list but are hidden from selections.",
            disabled=is_new,
        )
        delete_clicked = c3.button(
            "Delete",
            type="secondary",
            width="stretch",
            key=f"{state_key}_delete",
            disabled=is_new,
        )

        if delete_clicked and not is_new:
            try:
                delete_account(int(account_id), user_id)
            except (ValueError, sqlite3.Error) as exc:
                st.error(f"Failed to delete account: {exc}")
                return
            _reset_account_state()
            st.session_state[ACCOUNT_SUCCESS_STATE] = "Account deleted."
            close_dialog()
            st.rerun()

        if archive_clicked and not is_new:
            try:
                set_account_archived(int(account_id), user_id, archived=not archived)
            except (ValueError, sqlite3.Error) as exc:
                st.error(f"Failed to update archive status: {exc}")
                return
            st.session_state[ACCOUNT_SUCCESS_STATE] = (
                "Account restored." if archived else "Account archived."
            )
            st.rerun()

        if save_clicked:
            name_clean = (name_value or "").strip()
            if not name_clean:
                st.error("Provide the account name.")
                return

            if not balance_value:
                st.error("Provide the starting balance.")
                return

            payload: Dict[str, Any] = {
                "name": name_clean,
                "broker": (broker_value or "").strip() or None,
                "starting_balance": balance_value,
                "is_prop": 1 if is_prop_value else 0,
            }

            try:
                if is_new:
                    new_id = create_account(
                        user_id,
                        payload["name"],
                        payload["broker"],
                        "USD",
                        payload["starting_balance"],
                        payload["is_prop"],
                    )
                    st.session_state[ACCOUNT_SUCCESS_STATE] = "Account created."
                    _reset_account_state()
                    close_dialog()
                else:
                    update_account(int(account_id), user_id, payload)
                    st.session_state[ACCOUNT_SUCCESS_STATE] = "Account saved."
            except (ValueError, sqlite3.Error) as exc:
                st.error(f"Failed to save account: {exc}")
                return

            st.cache_data.clear()
            st.rerun()

    if dialog_is_active(ACCOUNT_DIALOG_NAME):
        _dialog()


def _get_dialog_title(data: Dict[str, Any], is_new: bool) -> str:
    if is_new:
        return "New account"
    return (data.get("name") or "Account").strip()


def _handle_dialog_dismiss() -> None:
    _reset_account_state()
    close_dialog()


def _reset_account_state() -> None:
    st.session_state.pop(ACCOUNT_ID_STATE, None)


__all__ = ["render_account_manager"]
