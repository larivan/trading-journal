from datetime import date, datetime, time
from typing import Any, Callable, Dict, List, Optional
from config import PAGES
import streamlit as st
import secrets


RESULT_LABELS = {
    "win": "Win",
    "loss": "Loss",
    "be": "Break-even",
    "miss": "Miss",
}


def is_win_rr(risk_reward: Optional[float]) -> bool:
    """Returns True if risk_reward qualifies as a Win."""
    from config import BE_THRESHOLD
    return risk_reward is not None and risk_reward > BE_THRESHOLD


def is_loss_rr(risk_reward: Optional[float]) -> bool:
    """Returns True if risk_reward qualifies as a Loss."""
    from config import BE_THRESHOLD
    return risk_reward is not None and risk_reward < -BE_THRESHOLD


def calculate_trade_result(risk_reward: Optional[float], is_missed: int) -> str:
    """Calculates trade result based on risk_reward and is_missed flag."""
    if is_missed:
        return "Miss"
    if risk_reward is None:
        return ""
    if is_win_rr(risk_reward):
        return "Win"
    if is_loss_rr(risk_reward):
        return "Loss"
    return "BE"


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
    return None


def parse_date(value: Optional[str]) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def to_option_format(
    items: List[Dict[str, Any]],
    *,
    formatter: Callable[[Dict[str, Any]], str],
) -> List[Dict[str, Any]]:
    """Приводит элементы к списку с явными label/value, сохраняя дубликаты."""
    options: List[Dict[str, Any]] = []
    for item in items:
        item_id = item.get("id")
        if item_id is None:
            continue
        options.append({"label": formatter(item), "value": item_id})
    return options


def custom_selectbox(
    label: str,
    options: List[Dict[str, Any]],
    *,
    placeholder: Optional[str] = None,
    value: Optional[int] = None,
    key: Optional[str] = None,
    on_change: Optional[Callable[[], None]] = None
) -> Optional[int]:
    """Единый selectbox для options [{'label','value'}] с поддержкой дефолтов."""
    has_options = bool(options)
    available = options if has_options else []
    index: Optional[int] = None
    if value is not None:
        for idx, option in enumerate(available):
            if option.get("value") == value:
                index = idx
                break

    if key is None:
        key = secrets.token_hex(16)

    selection = st.selectbox(
        label,
        available,
        index=index,
        key=key,
        placeholder=placeholder if has_options else None,
        format_func=lambda option: option.get("label", "-"),
        on_change=on_change
    )
    return selection.get("value") if isinstance(selection, dict) else None


def safe_choice_index(options: List[str], value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return options.index(value)
    except ValueError:
        return None


def result_label(value: Optional[str]) -> str:
    if not value:
        return ""
    return RESULT_LABELS.get(value, value.replace("_", " ").title())


# --- Общие форматеры для таблиц ---
def format_local_date(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().strftime("%d.%m.%Y")
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
            return value[:5] if len(value) >= 5 else value
    return str(value)


def format_number(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def get_excerpt(value: Optional[str], limit: int) -> str:
    if not value:
        return ""
    text = value.strip()
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3].rstrip() + "..."
