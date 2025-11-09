"""UI-блоки Options-вкладки трейд-менеджера."""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
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
        estimation_value = st.feedback(
            "thumbs",
            default=int(defaults["estimation"] or 0),
            key=f"tm_estimation_{trade_key}",
        )
        return {
            "cold_thoughts": cold_thoughts_value,
            "estimation": estimation_value,
        }


def render_charts_block(*, trade_key: str, charts_editor: pd.DataFrame) -> pd.DataFrame:
    """Рендерит таблицу с графиками и возвращает обновлённый датафрейм."""
    st.markdown("#### Charts")
    st.caption(
        "Add a chart link (URL) and optional description. Preview is generated automatically."
    )
    charts_display_df = charts_editor.copy()
    charts_display_df["preview"] = charts_display_df["chart_url"]
    edited_charts = st.data_editor(
        charts_display_df,
        hide_index=True,
        key=f"tm_charts_{trade_key}",
        num_rows="dynamic",
        column_config={
            "chart_url": st.column_config.TextColumn(
                "Link", help="TradingView, Telegram, etc."),
            "description": st.column_config.TextColumn(
                "Description", help="Optional comment"),
            "preview": st.column_config.ImageColumn(
                "Preview",
                help="Thumbnail will load automatically",
                width="medium",
            ),
        },
        column_order=["chart_url", "description", "preview"],
    )
    if edited_charts is None:
        return charts_editor.copy()
    return edited_charts.drop(columns=["preview"], errors="ignore").copy()


def render_notes_block(
        *,
        trade_key: str,
        notes_state_key: str,
        observations_editor: pd.DataFrame,
        tag_options: List[str],
) -> pd.DataFrame:
    """Отображает таблицу заметок и отдаёт актуальный датафрейм."""
    st.markdown("#### Trade observations")
    st.caption(
        "Add short observations for the trade. You can keep multiple notes.")
    edited = st.data_editor(
        observations_editor,
        hide_index=True,
        key=f"tm_observations_{trade_key}",
        column_config={
            "id": st.column_config.NumberColumn(
                "ID", disabled=True, width="small"),
            "title": st.column_config.TextColumn("Title"),
            "body": st.column_config.TextColumn(
                "Note", width="medium"),
            "tags": st.column_config.MultiselectColumn(
                "Tags",
                help="Optional markers for filtering",
                options=tag_options,
                accept_new_options=True,
                default=[],
            ),
        },
        column_order=["id", "title", "body", "tags"],
    )
    spacer_col, button_col = st.columns([0.7, 0.3])
    with button_col:
        add_clicked = st.button(
            "Add note",
            key=f"tm_add_note_{trade_key}",
            use_container_width=True,
        )
    if add_clicked:
        new_row = {
            "id": None,
            "title": "",
            "body": "",
            "tags": [],
        }
        edited = pd.concat(
            [edited, pd.DataFrame([new_row])], ignore_index=True)
        st.session_state[notes_state_key] = edited
    return edited


def render_header_actions(trade_key: str, *, is_create: bool) -> bool:
    """Кнопка для запуска сохранения/создания сделки."""
    label = "Create trade" if is_create else "Save changes"
    return st.button(
        label,
        type="primary",
        key=f"tm_submit_{trade_key}",
        use_container_width=True,
    )
