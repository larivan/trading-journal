"""Секция управления списком планов внутри этапа plan."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

import streamlit as st

from components.chart_editor import (
    chart_table_rows,
    render_chart_editor,
)
from db import (
    add_analysis_stage,
    delete_analysis_stage,
    list_analysis_stage_charts,
)

from ..constants import STAGE_TITLES


def render_plan_section(
    *,
    plan_stages: List[Dict[str, Any]],
    analysis_id: int,
    visible: bool,
    expanded: bool,
) -> List[Dict[str, Any]]:
    """Отображает список планов и возвращает их формы."""

    if not visible:
        return []

    stage_label = STAGE_TITLES.get("plan", "Plan")
    forms: List[Dict[str, Any]] = []

    with st.expander(stage_label, expanded=expanded):
        if st.button(
            "Добавить план",
            type="secondary",
            use_container_width=True,
            key=f"plan_add_{analysis_id}",
        ):
            add_analysis_stage(
                {
                    "analysis_id": analysis_id,
                    "type": "plan",
                    "time_local": datetime.now().strftime("%H:%M:%S"),
                    "summary": None,
                }
            )
            st.success("План создан.")
            st.rerun()

        if not plan_stages:
            st.info("Планы ещё не созданы.")
            return []

        for idx, stage in enumerate(sorted(plan_stages, key=lambda s: s.get("id") or 0), start=1):
            stage_id = stage["id"]
            st.markdown(f"#### План #{idx}")
            summary_value = st.text_area(
                "Описание",
                value=stage.get("summary") or "",
                height=200,
                key=f"plan_summary_{stage_id}",
            )

            charts = list_analysis_stage_charts(stage_id)
            chart_rows_source = chart_table_rows(charts)
            chart_editor_value = render_chart_editor(
                key=f"plan_chart_editor_{stage_id}",
                base_rows=chart_rows_source,
                title="Чарты",
                caption=None,
            )

            delete_col = st.columns(2)[1]
            if delete_col.button(
                "Удалить план",
                type="secondary",
                use_container_width=True,
                key=f"plan_delete_{stage_id}",
            ):
                try:
                    delete_analysis_stage(stage_id)
                    st.success("План удалён.")
                    st.rerun()
                except Exception as exc:  # pragma: no cover
                    st.error(f"Не удалось удалить план: {exc}")

            forms.append(
                {
                    "stage_id": stage_id,
                    "stage_type": "plan",
                    "summary": summary_value,
                    "charts": {
                        "attached": charts,
                        "rows_source": chart_rows_source,
                        "editor_value": chart_editor_value,
                    },
                }
            )

    return forms


__all__ = ["render_plan_section"]
