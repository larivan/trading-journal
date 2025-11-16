"""Утилиты состояния и вспомогательные функции для этапов анализа."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from config import ANALYSIS_STATE_VALUES
from db import add_analysis_stage, get_analysis_stage, list_analysis_stages


def visible_stage_types(current_stage: str) -> List[str]:
    """Возвращает последовательность этапов, которые должны отображаться."""

    if current_stage not in ANALYSIS_STATE_VALUES:
        return [ANALYSIS_STATE_VALUES[0]]
    idx = ANALYSIS_STATE_VALUES.index(current_stage)
    return ANALYSIS_STATE_VALUES[: idx + 1]


def ensure_stage_records(analysis_id: int) -> Dict[str, Dict[str, Any]]:
    """Гарантирует наличие записей для всех этапов анализа и возвращает их карту."""

    stage_map: Dict[str, Dict[str, Any]] = {}
    for stage in list_analysis_stages({"analysis_id": analysis_id}):
        stage_map[stage["type"]] = stage
    for stage_type in ANALYSIS_STATE_VALUES:
        if stage_type in stage_map:
            continue
        new_id = add_analysis_stage(
            {
                "analysis_id": analysis_id,
                "type": stage_type,
                "time_local": datetime.now().strftime("%H:%M:%S"),
                "summary": None,
            }
        )
        new_stage = get_analysis_stage(new_id)
        if new_stage:
            stage_map[stage_type] = new_stage
        else:  # fallback
            stage_map[stage_type] = {
                "id": new_id,
                "analysis_id": analysis_id,
                "type": stage_type,
                "time_local": datetime.now().strftime("%H:%M:%S"),
                "summary": None,
            }
    return stage_map


__all__ = ["visible_stage_types", "ensure_stage_records"]
