# db/ package - SQLite database layer for Trading Workspace
# Re-exports all public functions for backwards compatibility

from db.connection import (
    get_conn,
    transaction,
    init_db,
    DB_PATH,
    BASE_DIR,
)

from db.users import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_settings,
    update_user_settings,
    list_users,
    WRITABLE_SETTING_FIELDS,
)

from db.accounts import (
    create_account,
    list_accounts,
    get_account,
    update_account,
    delete_account,
    set_account_archived,
)

from db.setups import (
    create_setup,
    list_setups,
    get_setup,
    update_setup,
    delete_setup,
    SETUP_SELECT_COLUMNS,
    SETUP_WRITABLE_FIELDS,
    SETUP_ORDER_COLUMNS,
)

from db.notes import (
    create_note,
    list_notes,
    get_note,
    update_note,
    delete_note,
    attach_note_to_trade,
    detach_note_from_trade,
    list_trade_notes,
    count_notes_by_trade,
    attach_note_to_analysis,
    detach_note_from_analysis,
    list_analysis_notes,
    count_notes_by_analysis,
    NOTE_SELECT_COLUMNS,
    NOTE_WRITABLE_FIELDS,
    NOTE_ORDER_COLUMNS,
)

from db.analysis import (
    add_analysis,
    list_analysis,
    get_analysis,
    update_analysis,
    delete_analysis,
    ANALYSIS_COLUMNS,
    ANALYSIS_WRITABLE_FIELDS,
    ANALYSIS_ORDER_COLUMNS,
)

from db.images import (
    add_image,
    get_image,
    update_image,
    delete_image,
    list_images,
    attach_image,
    detach_image,
    attach_image_to_trade,
    detach_image_from_trade,
    attach_image_to_setup,
    detach_image_from_setup,
    attach_image_to_note,
    detach_image_from_note,
)

from db.trades import (
    create_trade,
    list_trades,
    get_trade_by_id,
    update_trade,
    delete_trade,
    TRADE_COLUMNS,
    TRADE_ORDER_COLUMNS,
    WRITABLE_TRADE_FIELDS,
)

__all__ = [
    # Connection
    "get_conn",
    "transaction",
    "init_db",
    "DB_PATH",
    "BASE_DIR",
    # Users
    "create_user",
    "get_user_by_email",
    "get_user_by_id",
    "get_user_settings",
    "update_user_settings",
    "list_users",
    "WRITABLE_SETTING_FIELDS",
    # Accounts
    "create_account",
    "list_accounts",
    "get_account",
    "update_account",
    "delete_account",
    "set_account_archived",
    # Setups
    "create_setup",
    "list_setups",
    "get_setup",
    "update_setup",
    "delete_setup",
    "SETUP_SELECT_COLUMNS",
    "SETUP_WRITABLE_FIELDS",
    "SETUP_ORDER_COLUMNS",
    # Notes
    "create_note",
    "list_notes",
    "get_note",
    "update_note",
    "delete_note",
    "attach_note_to_trade",
    "detach_note_from_trade",
    "list_trade_notes",
    "count_notes_by_trade",
    "attach_note_to_analysis",
    "detach_note_from_analysis",
    "list_analysis_notes",
    "count_notes_by_analysis",
    "NOTE_SELECT_COLUMNS",
    "NOTE_WRITABLE_FIELDS",
    "NOTE_ORDER_COLUMNS",
    # Analysis
    "add_analysis",
    "list_analysis",
    "get_analysis",
    "update_analysis",
    "delete_analysis",
    "ANALYSIS_COLUMNS",
    "ANALYSIS_WRITABLE_FIELDS",
    "ANALYSIS_ORDER_COLUMNS",
    # Images
    "add_image",
    "get_image",
    "attach_image",
    "detach_image",
    "update_image",
    "delete_image",
    "list_images",
    "attach_image_to_trade",
    "detach_image_from_trade",
    "attach_image_to_setup",
    "detach_image_from_setup",
    "attach_image_to_note",
    "detach_image_from_note",
    # Trades
    "create_trade",
    "list_trades",
    "get_trade_by_id",
    "update_trade",
    "delete_trade",
    "TRADE_COLUMNS",
    "TRADE_ORDER_COLUMNS",
    "WRITABLE_TRADE_FIELDS",
]
