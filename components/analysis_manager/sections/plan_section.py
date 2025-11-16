"""Секция управления списком планов внутри этапа plan."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

import streamlit as st

from components.chart_editor import (
    chart_table_rows,
    normalize_editor_rows,
    persist_chart_editor,
    render_chart_editor,
)
from db import (
    add_analysis_stage,
    delete_analysis_stage,
    list_analysis_stage_charts,
    update_analysis_stage,
    attach_chart_to_analysis_stage,
)

from ..constants import STAGE_TITLES


def render_plan_section(
    *,
    plan_stages: List[Dict[str, any]],
    analysis_id: int,
    visible: bool,
    expanded: bool,
) -> None:
    """Отображает список планов с отдельными чартами и описанием."""

    if not visible:
        return

    label = STAGE_TITLES.get("plan", "Plan")
    with st.expander(label, expanded=expanded):
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
            return

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

            col_save, col_delete = st.columns(2)
            if col_save.button(
                "Сохранить план",
                type="primary",
                use_container_width=True,
                key=f"plan_save_{stage_id}",
            ):
                try:
                    update_analysis_stage(
                        stage_id,
                        {
                            "analysis_id": analysis_id,
                            "type": "plan",
                            "summary": summary_value.strip() or None,
                            "time_local": datetime.now().strftime("%H:%M:%S"),
                        },
                    )
                    chart_state_payload = chart_editor_value if chart_editor_value is not None else chart_rows_source
                    editor_rows = normalize_editor_rows(chart_state_payload)
                    persist_chart_editor(
                        attached_charts=charts,
                        editor_rows=editor_rows,
                        attach_chart=lambda chart_id, s_id=stage_id: attach_chart_to_analysis_stage(
                            s_id, chart_id
                        ),
                    )
                    st.success("План обновлён.")
                    st.rerun()
                except Exception as exc:  # pragma: no cover
                    st.error(f"Не удалось сохранить план: {exc}")

            if col_delete.button(
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


__all__ = ["render_plan_section"]
