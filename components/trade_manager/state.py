"""Функции для работы с состояниями сделки."""

from typing import Dict, List

# Допустимые переходы между состояниями сделки (линейно)
STATE_TRANSITIONS: Dict[str, List[str]] = {
    "Open": ["Open", "Outcome"],
    "Outcome": ["Outcome", "Reviewed"],
    "Reviewed": ["Reviewed"],
}


def get_allowed_states(current_state: str) -> List[str]:
    """Возвращает доступные состояния для выбранной сделки."""
    if not current_state or current_state not in STATE_TRANSITIONS:
        return ["Open", "Outcome", "Reviewed"]
    return STATE_TRANSITIONS[current_state]


def visible_stages(selected_state: str) -> List[str]:
    """Определяет, какие блоки формы показывать для выбранного состояния."""
    if selected_state == "Open":
        return ["open"]
    if selected_state == "Outcome":
        return ["open", "outcome"]
    if selected_state == "Reviewed":
        return ["open", "outcome", "review"]
    return ["open"]
