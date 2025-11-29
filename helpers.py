from datetime import date, datetime, time
from typing import Any, Dict, List, Optional

from config import PAGES

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
def parse_time(value: Optional[str]) -> time:
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


def parse_date(value: Optional[str]) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return date.today()


def to_option_format(
    items: List[Dict[str, Any]],
    *,
    formatter,
) -> Dict[str, Optional[int]]:
    options: Dict = {}
    for item in items:
        options[formatter(item)] = item["id"]
    return options


def current_option_label(options: Dict[str, Optional[int]], value: Optional[int]) -> str:
    if not options:
        return None
    for label, option_value in options.items():
        if option_value == value:
            return label
    return next(iter(options))


def result_label(value: Optional[str]) -> str:
    if not value:
        return ""
    return RESULT_LABELS.get(value, value.replace("_", " ").title())


# --- Общие форматеры для таблиц ---
def format_local_date(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
            return parsed.strftime("%d.%m.%Y")
        except ValueError:
            return value
    return str(value)


def format_local_time(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
            return parsed.strftime("%H:%M")
        except ValueError:
            return value[:5]
    return str(value)


def format_number(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)
