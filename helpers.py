from datetime import date, datetime, time
from typing import Any, Dict, List, Optional

from config import PAGES

# --- Общие словари подписей для статусов/результатов сделок ---
STATE_LABELS = {
    "open": "Open",
    "closed": "Closed",
    "reviewed": "Reviewed",
    "cancelled": "Cancelled",
    "missed": "Missed",
}

RESULT_LABELS = {
    "win": "Win",
    "loss": "Loss",
    "be": "Break-even",
}


def apply_page_config(page_key: str):
    import streamlit as st
    options = PAGES.get(page_key)
    st.set_page_config(
        page_title=options['title'],
        page_icon=options["icon"],
        layout=options["layout"]
    )
    st.title(f"{options['icon']} {options['title']}")


def apply_page_config_from_file(file):
    from pathlib import Path
    return apply_page_config(Path(file).stem)


# --- Trade helpers (можно переиспользовать в различных компонентах) ---
def parse_trade_time(value: Optional[str]) -> time:
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                continue
    now = datetime.now().time()
    return time(hour=now.hour, minute=now.minute, second=0)


def parse_trade_date(value: Optional[str]) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return date.today()


def option_with_placeholder(
    items: List[Dict[str, Any]],
    *,
    placeholder: str,
    formatter,
) -> Dict[str, Optional[int]]:
    options: Dict[str, Optional[int]] = {placeholder: None}
    for item in items:
        options[formatter(item)] = item["id"]
    return options


def current_option_label(options: Dict[str, Optional[int]], value: Optional[int]) -> str:
    for label, option_value in options.items():
        if option_value == value:
            return label
    return next(iter(options))


def state_label(value: Optional[str]) -> str:
    if not value:
        return ""
    return STATE_LABELS.get(value, value.replace("_", " ").title())


def result_label(value: Optional[str]) -> str:
    if not value:
        return ""
    return RESULT_LABELS.get(value, value.replace("_", " ").title())
