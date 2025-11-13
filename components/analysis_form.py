from datetime import date, time
from typing import Any, Dict, Optional

import streamlit as st

from config import ASSETS, DAILY_BIAS, LOCAL_TZ
from helpers import parse_trade_date, parse_trade_time


def build_analysis_form_defaults(
    analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    analysis = analysis or {}
    return {
        "date": parse_trade_date(analysis.get("date_local")),
        "time": parse_trade_time(analysis.get("time_local")),
        "local_tz": analysis.get("local_tz") or LOCAL_TZ,
        "asset": analysis.get("asset") or (ASSETS[0] if ASSETS else ""),
        "day_result": analysis.get("day_result") or "Не указано",
        "pre_market_summary": analysis.get("pre_market_summary") or "",
        "plan_summary": analysis.get("plan_summary") or "",
        "post_market_summary": analysis.get("post_market_summary") or "",
    }


def render_analysis_form(
    *,
    form_key: str,
    defaults: Dict[str, Any],
) -> Dict[str, Any]:
    date_col, time_col, tz_col = st.columns([0.4, 0.3, 0.3])
    date_value = date_col.date_input(
        "Дата",
        value=defaults["date"],
        key=f"{form_key}_date",
        format="DD.MM.YYYY",
    )
    time_value = time_col.time_input(
        "Время",
        value=defaults["time"],
        key=f"{form_key}_time",
        step=300,
    )
    tz_value = tz_col.text_input(
        "Часовой пояс",
        value=defaults["local_tz"],
        key=f"{form_key}_tz",
    )

    asset_value = st.text_input(
        "Инструмент",
        value=defaults["asset"],
        placeholder=ASSETS[0] if ASSETS else "EUR/USD",
        key=f"{form_key}_asset",
    )

    result_options = ["Не указано"] + DAILY_BIAS if DAILY_BIAS else [
        "Не указано"]
    result_index = (
        result_options.index(defaults["day_result"])
        if defaults["day_result"] in result_options
        else 0
    )
    day_result_value = st.selectbox(
        "Day result / bias",
        options=result_options,
        index=result_index,
        key=f"{form_key}_day_result",
    )

    pre_summary = st.text_area(
        "Pre-market summary",
        value=defaults["pre_market_summary"],
        key=f"{form_key}_pre_summary",
        height=120,
    )
    plan_summary = st.text_area(
        "Plan summary",
        value=defaults["plan_summary"],
        key=f"{form_key}_plan_summary",
        height=120,
    )
    post_summary = st.text_area(
        "Post-market summary",
        value=defaults["post_market_summary"],
        key=f"{form_key}_post_summary",
        height=120,
    )

    return {
        "date": date_value,
        "time": time_value,
        "local_tz": tz_value,
        "asset": asset_value,
        "day_result": day_result_value,
        "pre_market_summary": pre_summary,
        "plan_summary": plan_summary,
        "post_market_summary": post_summary,
    }


def serialize_analysis_values(values: Dict[str, Any]) -> Dict[str, Any]:
    def _clean_text(text: Optional[str]) -> Optional[str]:
        if text is None:
            return None
        stripped = text.strip()
        return stripped or None

    date_value: date = values["date"]
    time_value: time = values["time"]

    payload = {
        "date_local": date_value.isoformat(),
        "time_local": time_value.strftime("%H:%M:%S"),
        "local_tz": _clean_text(values.get("local_tz")),
        "asset": _clean_text(values.get("asset")),
        "pre_market_summary": _clean_text(values.get("pre_market_summary")),
        "plan_summary": _clean_text(values.get("plan_summary")),
        "post_market_summary": _clean_text(values.get("post_market_summary")),
    }
    day_result = values.get("day_result")
    if day_result and day_result != "Не указано":
        payload["day_result"] = day_result
    else:
        payload["day_result"] = None
    return payload
