"""UI-блоки Options-вкладки трейд-менеджера."""

from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from config import EMOTIONAL_PROBLEMS, RESULT_VALUES

from .constants import RESULT_PLACEHOLDER


def render_open_stage(
    *,
    trade_key: str,
    visible: bool,
    expanded: bool,
    defaults: Dict[str, Any],
    account_labels: List[str],
    assets: List[str],
    analysis_labels: List[str],
    setup_labels: List[str],
) -> Dict[str, Any]:
    """Отрисовывает блок открытия сделки (дата, счёт, сетап и риск)."""

    result = defaults.copy()
    if not visible:
        return result

    with st.expander("Opening details", expanded=expanded):
        oc1, oc2 = st.columns(2)
        result["date"] = oc1.date_input(
            "Date",
            value=result["date"],
            format="DD.MM.YYYY",
            key=f"tm_date_{trade_key}",
        )
        result["time"] = oc2.time_input(
            "Time",
            value=result["time"],
            key=f"tm_time_{trade_key}",
        )

        result["account_label"] = st.selectbox(
            "Account",
            account_labels,
            index=account_labels.index(result["account_label"]),
            key=f"tm_account_{trade_key}",
        )

        result["asset"] = st.selectbox(
            "Asset",
            assets,
            index=assets.index(result["asset"]),
            key=f"tm_asset_{trade_key}",
        )

        result["analysis_label"] = st.selectbox(
            "Daily analysis",
            analysis_labels,
            index=analysis_labels.index(result["analysis_label"]),
            key=f"tm_analysis_{trade_key}",
        )

        result["setup_label"] = st.selectbox(
            "Setup",
            setup_labels,
            index=setup_labels.index(result["setup_label"]),
            key=f"tm_setup_{trade_key}",
        )

        result["risk_pct"] = st.slider(
            "Risk per trade, %",
            min_value=0.5,
            max_value=2.0,
            value=float(result["risk_pct"]),
            step=0.1,
            key=f"tm_risk_{trade_key}",
        )
    return result


def render_closed_stage(
    *,
    trade_key: str,
    visible: bool,
    expanded: bool,
    defaults: Dict[str, Any],
    emotional_defaults: List[str],
) -> Tuple[Dict[str, Any], List[str]]:
    """Рисует секцию After close и возвращает введённые значения."""
    if not visible:
        return {}, emotional_defaults

    with st.expander("After close", expanded=expanded):
        cc1, cc2 = st.columns(2)
        result_options = [RESULT_PLACEHOLDER] + RESULT_VALUES
        result_value = cc1.selectbox(
            "Result",
            result_options,
            index=result_options.index(
                defaults["result"]) if defaults["result"] in result_options else 0,
            key=f"tm_result_{trade_key}",
            format_func=lambda value: value if value == RESULT_PLACEHOLDER else value.replace(
                '_', ' ').title(),
        )
        net_pnl_value = cc2.number_input(
            "Net PnL, $",
            value=float(defaults["net_pnl"]),
            step=1.0,
            key=f"tm_pnl_{trade_key}",
        )
        risk_reward_value = cc1.number_input(
            "R:R",
            value=float(defaults["risk_reward"]),
            step=0.1,
            key=f"tm_rr_{trade_key}",
        )
        reward_percent_value = cc2.number_input(
            "Reward %",
            value=float(defaults["reward_percent"]),
            step=0.5,
            key=f"tm_reward_{trade_key}",
        )

        hot_thoughts_value = st.text_area(
            "Hot thoughts",
            height=100,
            value=defaults["hot_thoughts"],
            key=f"tm_hot_{trade_key}",
        )
        updated_emotions = st.multiselect(
            "Emotional challenges",
            EMOTIONAL_PROBLEMS,
            default=emotional_defaults,
            key=f"tm_emotions_{trade_key}",
        )
        inputs = {
            "result": result_value,
            "net_pnl": net_pnl_value,
            "risk_reward": risk_reward_value,
            "reward_percent": reward_percent_value,
            "hot_thoughts": hot_thoughts_value,
        }
    return inputs, updated_emotions


def render_review_stage(
    *,
    trade_key: str,
    visible: bool,
    expanded: bool,
    defaults: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Показывает блок Review, если он нужен для текущего статуса."""
    if not visible:
        return None

    with st.expander("Trade review", expanded=expanded):
        cold_thoughts_value = st.text_area(
            "Cold thoughts",
            height=120,
            value=defaults["cold_thoughts"],
            key=f"tm_cold_{trade_key}",
        )
        estimation_default = defaults.get("estimation")
        feedback_kwargs: Dict[str, Any] = {}
        if estimation_default in (0, 1):
            feedback_kwargs["default"] = int(estimation_default)

        estimation_value = st.feedback(
            "thumbs",
            key=f"tm_estimation_{trade_key}",
            **feedback_kwargs,
        )
        normalized_estimation = estimation_value if estimation_value in (
            0, 1) else None
        return {
            "cold_thoughts": cold_thoughts_value,
            "estimation": normalized_estimation,
        }


def render_header_actions(trade_key: str, trade_id: Optional[int] = None) -> bool:
    """Кнопки действия в заголовке: открыть сделку и сохранить изменения."""
    col_save, col_open = st.columns(2, gap="small")
    submitted = col_save.button(
        "Save changes",
        type="primary",
        key=f"tm_submit_{trade_key}",
        use_container_width=True,
    )
    with col_open:
        trade_url = f"/trade?id={trade_id}" if trade_id is not None else None
        col_open.link_button(
            "Open in new tab",
            url=trade_url or "#",
            disabled=trade_url is None,
            use_container_width=True,
        )
    return submitted
