"""Функции для работы со статусами сделок."""

from typing import List

from .constants import STATUS_STAGE, STATUS_TRANSITIONS


def allowed_statuses(current_state: str) -> List[str]:
    """Возвращает полный список статусов, куда можно перейти, включая обратные."""

    forward = STATUS_TRANSITIONS.get(current_state, ["open"])
    backward = [
        state for state, options in STATUS_TRANSITIONS.items()
        if current_state in options
    ]
    ordered: List[str] = []
    for candidate in forward + backward + [current_state]:
        if candidate not in ordered:
            ordered.append(candidate)
    return ordered or ["open"]


def visible_stages(selected_state: str) -> List[str]:
    """Определяет, какие блоки формы показывать для выбранного статуса."""

    stage = STATUS_STAGE.get(selected_state, "open")
    if stage == "open":
        return ["open"]
    if stage == "closed":
        return ["open", "closed"]
    if stage == "review":
        return ["open", "closed", "review"]
    return ["open"]
