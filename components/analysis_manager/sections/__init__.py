"""Секции интерфейса менеджера анализа."""

from .pre_section import render_pre_stage
from .post_section import render_post_stage
from .plan_section import render_plan_section
from .execution_section import render_execution_stage

__all__ = ["render_pre_stage", "render_post_stage", "render_plan_section", "render_execution_stage"]
