"""Построение значений по умолчанию для диалогов анализа."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

from config import ANALYSIS_STATE_VALUES, ASSETS, DAILY_BIAS, DAY_RESULT_VALUES


def build_analysis_defaults(analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Формирует словарь полей анализа, заполняя пропуски значениями по умолчанию."""

    analysis = analysis or {}
    return {
        "date_local": analysis.get("date_local") or date.today().isoformat(),
        "asset": analysis.get("asset") or (ASSETS[0] if ASSETS else ""),
        "state": analysis.get("state") or (ANALYSIS_STATE_VALUES[0] if ANALYSIS_STATE_VALUES else None),
        "daily_bias": analysis.get("daily_bias") or (DAILY_BIAS[0] if DAILY_BIAS else None),
        "fact_bias": analysis.get("fact_bias") or (DAILY_BIAS[0] if DAILY_BIAS else None),
        "day_result": analysis.get("day_result") or (DAY_RESULT_VALUES[0] if DAY_RESULT_VALUES else None),
    }


__all__ = ["build_analysis_defaults"]
