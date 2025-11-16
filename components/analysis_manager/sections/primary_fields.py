"""Отдельная секция с основными полями анализа."""

from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from config import ASSETS


def render_primary_fields(*, form_key: str, defaults: Dict[str, Any]) -> Dict[str, Any]:
    """Рендерит поля даты и актива и возвращает выбранные значения."""

    date_value = st.date_input(
        "Date",
        value="today",
        format="DD.MM.YYYY",
        key=f"{form_key}_date",
    )
    asset_value = st.selectbox(
        "Asset",
        options=ASSETS,
        index=ASSETS.index(defaults["asset"]) if defaults["asset"] in ASSETS else 0,
        key=f"{form_key}_asset",
    )
    return {
        "date_local": date_value.isoformat(),
        "asset": asset_value,
    }


__all__ = ["render_primary_fields"]
