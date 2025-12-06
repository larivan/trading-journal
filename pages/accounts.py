from typing import Any, Dict, List

import streamlit as st

from components.account_manager import render_account_manager
from components.entity_table import render_entity_table
from config import ACCOUNT_DIALOG_NAME, ACCOUNT_ID_STATE
from db import delete_account, list_accounts
from helpers import apply_page_config_from_file
from utils.session_state import open_dialog


apply_page_config_from_file(__file__)

actions_col, _ = st.columns([0.2, 0.8])
with actions_col:
    if st.button("Create", type="primary", width="stretch"):
        st.session_state.pop(ACCOUNT_ID_STATE, None)
        open_dialog(ACCOUNT_DIALOG_NAME)

rows = list_accounts(include_archived=True)


def _bool_label(value: Any) -> str:
    return "Yes" if value else "No"


account_columns: List[Dict[str, Any]] = [
    {"field": "name", "label": "Name", "id": "name"},
    {"field": "broker", "label": "Broker", "id": "broker"},
    {
        "field": "starting_balance",
        "label": "Starting balance",
        "id": "starting_balance",
        "format": lambda v: f"{float(v):.2f}" if v is not None else "",
    },
    {
        "field": "is_prop",
        "label": "Prop",
        "id": "is_prop",
        "format": _bool_label,
    },
    {
        "field": "archived",
        "label": "Archived",
        "id": "archived",
        "format": _bool_label,
    },
]


def _open_account(row: Dict[str, Any]) -> None:
    account_id = row.get("id")
    if account_id is None:
        return
    st.session_state[ACCOUNT_ID_STATE] = account_id
    open_dialog(ACCOUNT_DIALOG_NAME)


def _delete_accounts(ids: List[Any]) -> None:
    if not ids:
        return
    for account_id in ids:
        try:
            delete_account(int(account_id))
        except Exception as exc:
            st.toast(f"Failed to delete account #{account_id}: {exc}", icon="❌")
    st.rerun()


table_key = "accounts_table"
render_entity_table(
    entity_name="account",
    key=table_key,
    rows=rows,
    columns=account_columns,
    empty_message="Нет аккаунтов.",
    page_size=100,
    on_open=_open_account,
    on_delete=_delete_accounts,
)

render_account_manager()
