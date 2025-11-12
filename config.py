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
STATE_VALUES = ["open", "closed", "reviewed", "cancelled", "missed"]
RESULT_VALUES = ["win", "loss", "be"]
SESSION_VALUES = ["Frankfurt", "LOKZ", "Lunch", "Pre-NY", "NYKZ", "Other"]
ANALYSIS_SECTIONS = ["pre", "plan", "post"]

# --- Дополнительные справочники для UI ---
ASSETS = ["EUR/USD", "GBP/USD", "XAU/USD", "XAG/USD"]
DAILY_BIAS = ["Bullish", "Bearish", "Neutral"]
SETUPS = ["POI→confirmation", "Lq→confirmation", "POI→trigger→confirmation"]
EMOTIONAL_PROBLEMS = ["emotional management",
                      "premature exit", "fear of entry"]

LOCAL_TZ = 'UTC+3'  # Москва
