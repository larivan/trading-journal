"""Функции для работы со статусами сделок."""

from typing import Dict, List, Optional

# --- Допустимые переходы между статусами сделки ---
STATUS_TRANSITIONS: Dict[str, List[str]] = {
    "Open": ["Open", "Close", "Cancel"],
    "Close": ["Open", "Close", "Review"],
    "Review": ["Close", "Cancel", "Review"],
    "Cancel": ["Open", "Cancel", "Miss", "Review"],
    "Miss": ["Miss", "Review"],
}

# Маппинг статуса на итог сделки (outcome)
OUTCOME_BY_STATUS: Dict[str, str] = {
    "Open": "open",
    "Close": "closed",
    "Cancel": "canceled",
    "Miss": "missed",
}

DEFAULT_OUTCOME = "open"


def get_allowed_statuses(current_state: str) -> List[str]:
    """Возвращает объединённые переходы из текущего и предыдущего статусов."""
    if not current_state or current_state not in STATUS_TRANSITIONS:
        return ["Open", "Miss"]

    return STATUS_TRANSITIONS[current_state]


def visible_stages(selected_state: str) -> List[str]:
    """Определяет, какие блоки формы показывать для выбранного статуса."""
    if selected_state == "Open":
        return ["main"]
    if selected_state == "Close":
        return ["main", "close"]
    if selected_state == "Review":
        return ["main", "close", "review"]
    return ["main"]


def map_status_to_outcome(
    status: str,
    current_outcome: Optional[str] = None,
) -> str:
    """Возвращает итог сделки для выбранного статуса, оставляя текущее если статуса нет в мапе."""
    if status in OUTCOME_BY_STATUS:
        return OUTCOME_BY_STATUS[status]
    return current_outcome or DEFAULT_OUTCOME
