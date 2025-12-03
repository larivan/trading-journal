"""Построение значений по умолчанию для диалогов анализа."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from db import (
    list_charts,
    list_analysis_stages,
)


StageDefaults = Dict[str, Any]


def build_analysis_defaults(
    analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Формирует словарь полей анализа вместе с данными этапов."""

    analysis_id = analysis.get("id")
    stage_map: Dict[str, Dict[str, Any]] = {}
    plan_stages: List[Dict[str, Any]] = []
    if analysis_id:
        for stage in list_analysis_stages({"analysis_id": analysis_id}):
            if stage["type"] == "plan":
                plan_stages.append(stage)
            else:
                stage_map[stage["type"]] = stage
        plan_stages.sort(key=lambda item: item.get("id") or 0)

    return {
        "analysis": {
            "id": analysis_id,
            "date_local": analysis.get("date_local"),
            "asset": analysis.get("asset"),
            "state": analysis.get("state"),
            "daily_bias": analysis.get("daily_bias"),
            "fact_bias": analysis.get("fact_bias"),
            "day_result": analysis.get("day_result"),
        },
        "stages": {
            "pre-market": _build_stage_defaults(stage=stage_map.get("pre-market")),
            "post-market": _build_stage_defaults(stage=stage_map.get("post-market")),
        },
        "plans": _build_plan_defaults(plan_stages),
    }


def _build_stage_defaults(
    *,
    stage: Optional[Dict[str, Any]],
) -> StageDefaults:
    stage_id = stage.get("id") if stage else None
    base: StageDefaults = {
        "stage_id": stage_id,
        "summary": (stage.get("summary") if stage else None) or "",
        "charts": list_charts(analysis_stage_id=stage_id) if stage_id else [],
        "time_local": stage.get("time_local") if stage else None,
    }
    return base


def _build_plan_defaults(stages):
    defaults = [_build_stage_defaults(stage=stage) for stage in stages]
    if not defaults:
        defaults.append(_build_stage_defaults(stage=None))
    return defaults


__all__ = ["build_analysis_defaults", "StageDefaults"]
