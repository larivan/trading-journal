
PAGES = {
    'dashboard': {
        'title': 'Dashboard',
        'icon': ':material/bar_chart:',
        'default': True,
        'layout': 'wide',
    },
    'analysis': {
        'title': 'Analysis Database',
        'icon': ':material/insights:',
        'default': False,
        'layout': 'wide',
    },
    'trades': {
        'title': 'Trades Database',
        'icon': ':material/view_list:',
        'default': False,
        'layout': 'wide',
    },
    'notes': {
        'title': 'Observations',
        'icon': ':material/sticky_note_2:',
        'default': False,
        'layout': 'wide',
    },
    'setups': {
        'title': 'Setups',
        'icon': ':material/grid_view:',
        'default': False,
        'layout': 'wide',
    },
    'settings_accounts': {
        'title': 'Accounts',
        'icon': ':material/account_balance_wallet:',
        'default': False,
        'layout': 'wide',
    },
    'settings': {
        'title': 'Settings',
        'icon': ':material/settings:',
        'default': False,
        'layout': 'wide',
    },
}

SETTINGS_PAGES = {}

EDITOR_PAGES = {
    "trade_editor": {"title": "Trade Editor", "icon": ":material/edit:", "default": False},
    "analysis_editor": {"title": "Analysis Editor", "icon": ":material/edit:", "default": False},
}

LOCAL_TZ = 'Europe/Moscow'

# Trades
TRADE_DIALOG_NAME = "trade_manager"
TRADE_ID_STATE = "tm_trade_id"
TRADE_SUCCESS_STATE = "tm_success_message"
TM_KEY_PREFIX = "tm_trade_id_"
TM_DEFAULT_PREFIX = "tm_default_"
TM_DEFAULT_ANALYSIS_ID_STATE = "tm_default_analysis_id"
TRADE_STATUS_VALUES = ["Open", "Outcome", "Reviewed"]  # computed, not stored
TRADE_TYPE_VALUES = ["Intraday", "Swing"]
TRADE_RESULT_VALUES = ["Win", "Loss", "BE", "Miss"]
BE_THRESHOLD = 0.05
TRADE_SESSION_VALUES = ["Frankfurt", "LOKZ",
                        "Lunch", "Pre-NY", "NYKZ", "Other"]
DEFAULT_MISTAKE_TYPES = [
    "Early entry",
    "Late entry",
    "Wrong stop placement",
    "Broke trading plan",
    "Emotional entry",
    "Wrong session / time",
    "Missed setup criteria",
]

# Accounts
ACCOUNT_DIALOG_NAME = "account_manager"
ACCOUNT_ID_STATE = "acc_account_id"
ACCOUNT_SUCCESS_STATE = "acc_success_message"
ACCOUNT_MANAGER_KEY_PREFIX = "acc_account_id_"

# Analysis
ANALYSIS_DIALOG_NAME = "analysis_manager"
ANALYSIS_ID_STATE = "am_analysis_id"
ANALYSIS_SUCCESS_STATE = "am_success_message"
ANALYSIS_MANAGER_KEY_PREFIX = "am_analysis_id_"
ANALYSIS_STATE_VALUES = ["pre-market", "plan", "execution", "post-market"]
ASSETS_VALUES = ["EUR/USD", "GBP/USD", "XAU/USD", "XAG/USD"]
DAILY_BIAS_VALUES = ["Bullish", "Bearish", "Neutral"]
DAY_RESULT_VALUES = ["profit", "loss", "null"]

# Notes
NOTE_DIALOG_NAME = "note_manager"
NOTE_ID_STATE = "nm_note_id"
NOTE_SUCCESS_STATE = "nm_success_message"
NOTE_MANAGER_KEY_PREFIX = "nm_note_id_"

# Setups
SETUP_DIALOG_NAME = "setup_manager"
SETUP_ID_STATE = "sm_setup_id"
SETUP_SUCCESS_STATE = "sm_success_message"
SETUP_MANAGER_KEY_PREFIX = "sm_setup_id_"
