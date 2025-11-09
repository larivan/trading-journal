"""Вкладка View для отображения сделки в удобном виде."""

from typing import Any, Dict, List, Optional

import streamlit as st

from db import parse_emotional_problems
from helpers import result_label, state_label


def _format_view_value(value: Optional[Any], placeholder: str = "—") -> str:
    """Единое форматирование числовых и текстовых значений для вкладки View."""
    if value is None:
        return placeholder
    if isinstance(value, float):
        formatted = f"{value:.2f}".rstrip("0").rstrip(".")
        return formatted or "0"
    text_value = str(value).strip()
    return text_value or placeholder


def render_view_tab(
    trade: Dict[str, Any],
    trade_notes: List[Dict[str, Any]],
    trade_charts: List[Dict[str, Any]],
    *,
    account_label: str,
    setup_label: str,
    analysis_label: str,
) -> None:
    st.markdown("#### Trade overview")
    summary_col1, summary_col2 = st.columns(2)
    summary_col1.markdown(f"**Status:** {state_label(trade.get('state')) or '—'}")
    summary_col1.markdown(f"**Result:** {result_label(trade.get('result')) or '—'}")
    summary_col1.markdown(f"**Date:** {_format_view_value(trade.get('date_local'))}")
    summary_col1.markdown(f"**Time:** {_format_view_value(trade.get('time_local'))}")

    summary_col2.markdown(f"**Account:** {account_label or '—'}")
    summary_col2.markdown(f"**Setup:** {setup_label or '—'}")
    summary_col2.markdown(f"**Analysis:** {analysis_label or '—'}")

    st.divider()
    st.markdown("#### After close")
    close_col1, close_col2 = st.columns(2)
    close_col1.metric("Net PnL", _format_view_value(trade.get('net_pnl')))
    close_col1.metric("R:R", _format_view_value(trade.get('risk_reward')))
    close_col2.metric("Reward %", _format_view_value(trade.get('reward_percent')))
    emotions = parse_emotional_problems(trade.get('emotional_problems'))
    close_col2.metric("Emotions", ", ".join(emotions) if emotions else "—")
    st.write(f"**Hot thoughts:** {_format_view_value(trade.get('hot_thoughts'))}")

    st.divider()
    st.markdown("#### Review")
    st.write(f"**Cold thoughts:** {_format_view_value(trade.get('cold_thoughts'))}")
    st.write(f"**Estimation:** {_format_view_value(trade.get('estimation'))}")

    st.divider()
    st.markdown("#### Charts")
    if not trade_charts:
        st.caption("Charts not attached")
    else:
        for idx, chart in enumerate(trade_charts, start=1):
            url = chart.get('chart_url') or '—'
            desc = chart.get('description') or chart.get('title') or ''
            st.markdown(f"{idx}. [{url}]({url}) — {desc}")

    st.divider()
    st.markdown("#### Notes")
    if not trade_notes:
        st.caption("No observations yet")
    else:
        for note in trade_notes:
            title = note.get('title') or f"Note #{note.get('id') or ''}".strip()
            with st.expander(title):
                st.write(note.get('body') or '—')
                tags = note.get('tags') or []
                if isinstance(tags, str):
                    tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
                st.caption(f"Tags: {', '.join(tags) if tags else '—'}")
