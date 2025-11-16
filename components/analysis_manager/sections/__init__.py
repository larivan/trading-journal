"""Секции интерфейса менеджера анализа."""

from .primary_fields import render_primary_fields
from .pre_section import render_pre_stage
from .post_section import render_post_stage
from .plan_section import render_plan_section

__all__ = ["render_primary_fields", "render_pre_stage", "render_post_stage", "render_plan_section"]
