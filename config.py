PAGES = {
    'dashboard': {
        'title': 'Dashboard',
        'icon': ':material/bar_chart:',
        'default': True,
        'layout': 'wide',
        'in_nav': True,
    },
    'trades': {
        'title': 'Journal',
        'icon': ':material/view_list:',
        'default': False,
        'layout': 'wide',
        'in_nav': True,
    },
    'add-trade': {
        'title': 'Add trade',
        'icon': ':material/inventory:',
        'default': False,
        'layout': 'wide',
        'in_nav': False,
    },
    'test': {
        'title': 'Test page',
        'icon': ':material/inventory:',
        'default': False,
        'layout': 'wide',
        'in_nav': False,
    },
}

# --- Справочники (энумы) ---
STATE_VALUES = ["open", "closed", "reviewed", "cancelled", "missed"]
RESULT_VALUES = ["win", "loss", "be"]
SESSION_VALUES = ["Frankfurt", "LOKZ", "Lunch", "Pre-NY", "NYKZ", "Other"]
ANALYSIS_SECTIONS = ["pre", "plan", "post"]
STATUS_VALUES = ["mistake", "success"]

# --- Дополнительные справочники для UI ---
ASSETS = ["EUR/USD", "GBP/USD", "XAU/USD", "XAG/USD"]
DAILY_BIAS = ["Bullish", "Bearish", "Neutral"]
SESSIONS = SESSION_VALUES
TRADE_TYPES = ["Intraday", "Swing"]
SETUPS = ["POI→confirmation", "Lq→confirmation", "POI→trigger→confirmation"]
TRADE_RESULTS = RESULT_VALUES
TRADE_STATUS = STATUS_VALUES
DAY_RESULTS = ["Profit", "Loss", "Missed opportunity"]
DIRECTIONS = [None, "buy", "sell"]
EMOTIONAL_PROBLEMS = ["emotional management",
                      "premature exit", "fear of entry"]
RISK_PERCENTS = [0.5, 1, 1.5, 2]

LOCAL_TZ = 'UTC+3'  # Москва
