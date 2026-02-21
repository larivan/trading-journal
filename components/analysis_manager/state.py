"""Функции для работы с состояниями анализа."""

from typing import List
from config import ANALYSIS_STATE_VALUES


def get_allowed_analysis_stages(current_stage: str) -> List[str]:
    """Возвращает допустимые стадии для выбора.

    Правила:
    - Вперёд только на один шаг (+1 от текущей стадии).
    - Назад — свободно (любая предыдущая стадия доступна).
    - Если стадия неизвестна — возвращается только первая.
    """
    if current_stage not in ANALYSIS_STATE_VALUES:
        return [ANALYSIS_STATE_VALUES[0]]
    current_idx = ANALYSIS_STATE_VALUES.index(current_stage)
    max_idx = min(current_idx + 1, len(ANALYSIS_STATE_VALUES) - 1)
    return ANALYSIS_STATE_VALUES[: max_idx + 1]


__all__ = ["get_allowed_analysis_stages"]
