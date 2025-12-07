"""Секции трейд-менеджера, разбитые по подмодулям."""

from .main_stage import render_main_stage
from .close_stage import render_close_stage
from .review_stage import render_review_stage

__all__ = [
    "render_main_stage",
    "render_close_stage",
    "render_review_stage",
]
