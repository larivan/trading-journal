"""Построение значений по умолчанию для диалогов анализа."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from config import ANALYSIS_STATE_VALUES, ASSETS, DAILY_BIAS, DAY_RESULT_VALUES
from db import (
    list_analysis_stage_charts,
    list_analysis_stage_notes,
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
            "pre-market": _build_stage_defaults(
                stage_type="pre-market",
                stage=stage_map.get("pre-market"),
            ),
            "post-market": _build_stage_defaults(
                stage_type="post-market",
                stage=stage_map.get("post-market"),
            ),
        },
        "plans": _build_plan_defaults(plan_stages),
    }


def _build_stage_defaults(
    *,
    stage_type: str,
    stage: Optional[Dict[str, Any]],
) -> StageDefaults:
    stage_id = stage.get("id") if stage else None
    base: StageDefaults = {
        "stage_id": stage_id,
        "summary": (stage.get("summary") if stage else None) or "",
        "charts": list_analysis_stage_charts(stage_id) if stage_id else [],
    }
    # if stage_type == "post-market":
    #     attached_notes = (
    #         list_analysis_stage_notes(stage_id) if stage_id else []
    #     )
    #     note_ids = [note["id"] for note in attached_notes]
    #     base.update(
    #         {
    #             "attached_notes": attached_notes,
    #             "note_ids": list(note_ids),
    #             "original_note_ids": list(note_ids),
    #         }
    #     )
    return base


def _build_plan_defaults(stages):
    defaults = [
        _build_stage_defaults(stage_type="plan", stage=stage)
        for stage in stages
    ]
    if not defaults:
        defaults.append(_build_stage_defaults(
            stage_type="plan", stage=None))
    return defaults


__all__ = ["build_analysis_defaults", "StageDefaults"]
