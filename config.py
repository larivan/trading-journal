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
    },
    'market_analysis': {
        'title': 'Market analysis',
        'icon': ':material/insights:',
        'default': False,
        'layout': 'wide',
        'in_nav': True,
    },
}

# --- Справочники (энумы) ---
TRADE_STATE_VALUES = ["open", "closed", "reviewed", "cancelled", "missed"]
TRADE_RESULT_VALUES = ["win", "loss", "be"]
TRADE_SESSION_VALUES = ["Frankfurt", "LOKZ",
                        "Lunch", "Pre-NY", "NYKZ", "Other"]

ANALYSIS_STATE_VALUES = ["pre-market", "plan", "trading", "post-market"]

# --- Дополнительные справочники для UI ---
ASSETS = ["EUR/USD", "GBP/USD", "XAU/USD", "XAG/USD"]
DAILY_BIAS = ["Bullish", "Bearish", "Neutral"]
DAY_RESULT_VALUES = ["profit", "loss", "null"]
SETUPS = ["POI→confirmation", "Lq→confirmation", "POI→trigger→confirmation"]
EMOTIONAL_PROBLEMS = ["emotional management",
                      "premature exit", "fear of entry"]

LOCAL_TZ = 'UTC+3'  # Москва


# --- Допустимые переходы между статусами сделки ---
STATUS_TRANSITIONS: Dict[str, List[str]] = {
    "open": ["open", "closed", "cancelled"],
    "closed": ["closed", "reviewed"],
    "reviewed": ["reviewed"],
    "cancelled": ["cancelled", "reviewed"],
    "missed": ["missed", "reviewed"],
}

# --- Карта статусов к визуальным стадиям (какие блоки формы показывать) ---
STATUS_STAGE = {
    "open": "open",
    "closed": "closed",
    "reviewed": "review",
    "cancelled": "open",
    "missed": "open",
}

# --- Значение-заглушка для селекта результата ---
RESULT_PLACEHOLDER = "— Not set —"

# --- Статусы, доступные при создании сделки ---
CREATE_ALLOWED_STATUSES = ["open", "missed"]
