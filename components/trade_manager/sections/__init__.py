"""Секции трейд-менеджера, разбитые по подмодулям."""

from .open_section import render_open_stage
from .closed_section import render_closed_stage
from .review_section import render_review_stage

__all__ = [
    "render_open_stage",
    "render_closed_stage",
    "render_review_stage",
]
