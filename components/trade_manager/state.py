"""Функции для работы со статусами сделок."""

from typing import Dict, List

# --- Допустимые переходы между статусами сделки ---
STATUS_TRANSITIONS: Dict[str, List[str]] = {
    "Open": ["Open", "Close", "Cancel"],
    "Close": ["Open", "Close", "Review"],
    "Review": ["Close", "Review"],
    "Cancel": ["Open", "Cancel", "Review"],
    "Miss": ["Miss", "Review"],
}


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
