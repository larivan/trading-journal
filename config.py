from typing import Dict, List

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
    'accounts': {
        'title': 'Accounts',
        'icon': ':material/account_balance_wallet:',
        'default': False,
        'layout': 'wide',
    },
}

LOCAL_TZ = 'UTC+3'  # Москва

# Trades
TRADE_DIALOG_NAME = "trade_manager"
TRADE_ID_STATE = "tm_trade_id"
TRADE_SUCCESS_STATE = "tm_success_message"
TM_KEY_PREFIX = "tm_trade_id_"
TM_DEFAULT_PREFIX = "tm_default_"
TRADE_STATE_VALUES = ["Open", "Close", "Review", "Cancel", "Miss"]
TRADE_OUTCOME_VALUES = ["open", "closed", "canceled", "missed"]
TRADE_RESULT_VALUES = ["Win", "Loss", "BE"]
TRADE_SESSION_VALUES = ["Frankfurt", "LOKZ",
                        "Lunch", "Pre-NY", "NYKZ", "Other"]

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
