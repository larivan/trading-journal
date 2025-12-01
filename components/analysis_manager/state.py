"""Утилиты состояния и вспомогательные функции для этапов анализа."""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Tuple
from config import ANALYSIS_STATE_VALUES
from db import add_analysis_stage, get_analysis_stage, list_analysis_stages


def visible_stage_types(current_stage: str) -> List[str]:
    """Возвращает последовательность этапов, которые должны отображаться."""

    if current_stage not in ANALYSIS_STATE_VALUES:
        return [ANALYSIS_STATE_VALUES[0]]
    idx = ANALYSIS_STATE_VALUES.index(current_stage)
    return ANALYSIS_STATE_VALUES[: idx + 1]


def ensure_stage_records(analysis_id: int) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """Гарантирует наличие записей для этапов и возвращает отдельные коллекции."""

    stages: Dict[str, Dict[str, Any]] = {}
    plans: List[Dict[str, Any]] = []
    for stage in list_analysis_stages({"analysis_id": analysis_id}):
        if stage["type"] == "plan":
            plans.append(stage)
        else:
            stages[stage["type"]] = stage

    for stage_type in ANALYSIS_STATE_VALUES:
        if stage_type == "plan":
            continue
        if stage_type in stages:
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
            stages[stage_type] = new_stage
        else:  # fallback
            stages[stage_type] = {
                "id": new_id,
                "analysis_id": analysis_id,
                "type": stage_type,
                "time_local": datetime.now().strftime("%H:%M:%S"),
                "summary": None,
            }

    plans.sort(key=lambda stage: stage.get("id") or 0)
    return stages, plans


__all__ = ["visible_stage_types", "ensure_stage_records"]
