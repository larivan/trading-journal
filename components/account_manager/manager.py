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
    set_account_archived,
    update_account,
)
from utils.auth import get_current_user_id
from utils.cached_data import cached_account, cached_trades, invalidate_accounts
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
        account = cached_account(int(account_id), user_id) or {}
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
            _CURRENCIES = ["USD", "EUR"]
            currency_value = st.selectbox(
                "Currency",
                _CURRENCIES,
                index=_CURRENCIES.index(account.get("currency") or "USD")
                if (account.get("currency") or "USD") in _CURRENCIES else 0,
                key=f"{state_key}_currency",
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
            currency = account.get("currency") or "USD"
            starting = float(account.get("starting_balance") or 0.0)
            trades = cached_trades(user_id)
            pnl = sum(
                t["net_pnl"] for t in trades
                if t.get("account_id") == account_id and t.get("net_pnl") is not None
            )
            st.markdown(f"**Broker:** {account.get('broker') or 'N/A'}")
            st.markdown(f"**Starting balance:** {currency} {starting:,.2f}")
            st.markdown(f"**Current balance:** {currency} {starting + pnl:,.2f}")

        archived = bool(account.get("archived"))
        if is_new:
            save_clicked = st.button(
                "Save",
                type="primary",
                width="stretch",
                key=f"{state_key}_save",
            )
            archive_clicked = False
            delete_clicked = False
        else:
            save_clicked = False
            c1, c2 = st.columns(2)
            archive_clicked = c1.button(
                "Restore" if archived else "Archive",
                type="secondary",
                width="stretch",
                key=f"{state_key}_archive",
                help="Archived accounts stay in the list but are hidden from selections.",
            )
            delete_clicked = c2.button(
                "Delete",
                type="secondary",
                width="stretch",
                key=f"{state_key}_delete",
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
                "currency": currency_value,
                "starting_balance": balance_value,
                "is_prop": 1 if is_prop_value else 0,
            }

            try:
                if is_new:
                    new_id = create_account(
                        user_id,
                        payload["name"],
                        payload["broker"],
                        currency_value,
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

            invalidate_accounts()
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
