from typing import Dict, List

PAGES = {
    'dashboard': {
        'title': 'Dashboard',
        'icon': ':material/bar_chart:',
        'default': True,
        'layout': 'wide',
        'in_nav': True,
    },
    'trades': {
        'title': 'Trades Database',
        'icon': ':material/view_list:',
        'default': False,
        'layout': 'wide',
        'in_nav': True,
    }
}

# --- Справочники (энумы) ---
TRADE_STATE_VALUES = ["open", "closed", "reviewed", "cancelled", "missed"]
TRADE_RESULT_VALUES = ["win", "loss", "be"]
TRADE_SESSION_VALUES = ["Frankfurt", "LOKZ",
                        "Lunch", "Pre-NY", "NYKZ", "Other"]

# --- Дополнительные справочники для UI ---
ASSETS = ["EUR/USD", "GBP/USD", "XAU/USD", "XAG/USD"]
DAILY_BIAS = ["Bullish", "Bearish", "Neutral"]
DAY_RESULT_VALUES = ["profit", "loss", "null"]
SETUPS = ["POI→confirmation", "Lq→confirmation", "POI→trigger→confirmation"]
EMOTIONAL_PROBLEMS = ["emotional management",
                      "premature exit", "fear of entry"]

LOCAL_TZ = 'UTC+3'  # Москва
