from datetime import date, datetime, time
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
import streamlit as st

from config import ASSETS, EMOTIONAL_PROBLEMS, RESULT_VALUES
from db import (
    create_trade,
    list_accounts,
    list_analysis,
    list_charts_for_trade,
    list_notes_for_trade,
    list_setups,
    parse_emotional_problems,
    replace_trade_charts,
    replace_trade_notes,
    update_trade,
)

# =============================================================================
# КОНСТАНТЫ И СЛУЖЕБНЫЕ СТРУКТУРЫ
# =============================================================================
# В этом блоке собраны все статусы и человеко-читаемые метки, чтобы не приходилось
# искать их по всему файлу. При необходимости дополняем значения именно здесь.
STATUS_TRANSITIONS: Dict[str, List[str]] = {
    "open": ["open", "closed", "cancelled", "missed"],
    "closed": ["closed", "reviewed"],
    "reviewed": ["reviewed"],
    "cancelled": ["cancelled"],
    "missed": ["missed"],
}

STATUS_STAGE = {
    "open": "open",
    "closed": "closed",
    "reviewed": "review",
    "cancelled": "open",
    "missed": "open",
}

RESULT_PLACEHOLDER = "— Not set —"
CREATE_ALLOWED_STATUSES = ["open", "missed"]

STATE_LABELS = {
    "open": "Open",
    "closed": "Closed",
    "reviewed": "Reviewed",
    "cancelled": "Cancelled",
    "missed": "Missed",
}

RESULT_LABELS = {
    "win": "Win",
    "loss": "Loss",
    "be": "Break-even",
}


# =============================================================================
# ОБЩИЕ ХЕЛПЕРЫ: парсинг дат, подготовка списков, сбор таблиц
# =============================================================================
def _state_label(value: Optional[str]) -> str:
    """Преобразуем технический статус в человеко-читаемое название."""

    if not value:
        return ""
    return STATE_LABELS.get(value, value.replace("_", " ").title())


def _result_label(value: Optional[str]) -> str:
    """Аналогичный хелпер для результата сделки."""

    if not value:
        return ""
    return RESULT_LABELS.get(value, value.replace("_", " ").title())


def _parse_time_value(value: Optional[str]) -> time:
    """Унифицируем входные значения времени для таймпикера."""

    if isinstance(value, time):
        return value
    if isinstance(value, str):
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                continue
    now = datetime.now().time()
    return time(hour=now.hour, minute=now.minute, second=0)


def _parse_date_value(value: Optional[str]) -> date:
    """Гарантируем корректный объект даты."""

    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return date.today()


def _option_with_placeholder(
    items: List[Dict[str, Any]],
    *,
    placeholder: str,
    formatter,
) -> Dict[str, Optional[int]]:
    """Формируем словарь "подпись -> id" с заглушкой."""

    options: Dict[str, Optional[int]] = {placeholder: None}
    for item in items:
        options[formatter(item)] = item["id"]
    return options


def _current_label(options: Dict[str, Optional[int]],
                   current_value: Optional[int]) -> str:
    """Находим текущую подпись по значению id."""

    for label, value in options.items():
        if value == current_value:
            return label
    return next(iter(options))


def _notes_dataframe(notes: List[Dict[str, Any]]) -> pd.DataFrame:
    """Превращаем список заметок в датафрейм для data_editor."""

    base_columns = ["id", "title", "body", "tags"]
    df = pd.DataFrame(notes or [])
    if df.empty:
        df = pd.DataFrame([{
            "id": None,
            "title": "",
            "body": "",
            "tags": [],
        }])
    for column in base_columns:
        if column not in df.columns:
            df[column] = "" if column != "id" else None
    df = df[base_columns]
    df["tags"] = df["tags"].apply(_split_tags)
    return df


def _charts_dataframe(charts: List[Dict[str, Any]]) -> pd.DataFrame:
    """Готовим датафрейм с графиками с обязательными колонками."""

    base_columns = ["chart_url", "description"]
    df = pd.DataFrame(charts or [])
    if df.empty:
        return pd.DataFrame(columns=base_columns)
    if "chart_url" not in df.columns:
        df["chart_url"] = ""
    if "description" not in df.columns:
        df["description"] = ""
    if "title" in df.columns:
        mask = df["description"].isna() | (df["description"] == "")
        df.loc[mask, "description"] = df.loc[mask, "title"].fillna("")
    df["chart_url"] = df["chart_url"].fillna("")
    df["description"] = df["description"].fillna("")
    return df[base_columns]


def _split_tags(raw_value: Any) -> List[str]:
    """Разбиваем строку тегов на список и чистим пробелы."""

    if isinstance(raw_value, list):
        candidates = raw_value
    elif raw_value is None or pd.isna(raw_value):
        candidates = []
    else:
        candidates = str(raw_value).split(",")
    normalized: List[str] = []
    for tag in candidates:
        if tag is None:
            continue
        tag_value = str(tag).strip()
        if tag_value:
            normalized.append(tag_value)
    return normalized


def _serialize_tags(raw_value: Any) -> Optional[str]:
    """Обратная операция для записи тегов в БД."""

    if isinstance(raw_value, list):
        normalized: List[str] = []
        for tag in raw_value:
            if tag is None or pd.isna(tag):
                continue
            tag_value = str(tag).strip()
            if tag_value:
                normalized.append(tag_value)
        return ", ".join(normalized) or None
    if raw_value is None or pd.isna(raw_value):
        return None
    raw_text = str(raw_value).strip()
    return raw_text or None


def _prepare_note_records(editor_df: Optional[pd.DataFrame],
                          existing_ids: Optional[Set[int]] = None) -> List[Dict[str, Any]]:
    """Нормализуем записи заметок перед replace_trade_notes."""

    if editor_df is None:
        return []
    existing_ids = {
        int(note_id) for note_id in (existing_ids or set()) if note_id is not None
    }
    working_df = editor_df.copy()
    if "id" not in working_df.columns:
        index_label = working_df.index.name or "index"
        working_df = working_df.reset_index().rename(
            columns={index_label: "id"})
    normalized_ids: List[Optional[int]] = []
    for raw_id in working_df["id"].tolist():
        try:
            candidate = int(raw_id)
        except (TypeError, ValueError):
            candidate = None
        normalized_ids.append(candidate if candidate in existing_ids else None)
    working_df["id"] = normalized_ids
    records: List[Dict[str, Any]] = []
    for row in working_df.to_dict("records"):
        records.append({
            "id": row.get("id"),
            "title": (row.get("title") or "").strip() or None,
            "body": (row.get("body") or "").strip(),
            "tags": _serialize_tags(row.get("tags")),
        })
    return records


def _prepare_chart_records(editor_df: Optional[pd.DataFrame]) -> List[Dict[str, Any]]:
    """Аналогичная нормализация для графиков."""

    if editor_df is None:
        return []
    records: List[Dict[str, Any]] = []
    for row in editor_df.to_dict("records"):
        chart_url = (row.get("chart_url") or "").strip()
        if not chart_url:
            continue
        description = (row.get("description") or "").strip()
        records.append({
            "title": description or None,
            "chart_url": chart_url,
            "description": description or None,
        })
    return records


def _allowed_statuses(current_state: str) -> List[str]:
    """Возвращаем разрешённые переходы для текущего статуса."""
    forward = STATUS_TRANSITIONS.get(current_state, ["open"])
    backward = [
        state for state, options in STATUS_TRANSITIONS.items()
        if current_state in options
    ]
    ordered: List[str] = []
    for candidate in forward + backward + [current_state]:
        if candidate not in ordered:
            ordered.append(candidate)
    return ordered or ["open"]


def _visible_stages(selected_state: str) -> List[str]:
    """Определяем, какие блоки формы показывать для выбранного статуса."""

    stage = STATUS_STAGE.get(selected_state, "open")
    if stage == "open":
        return ["open"]
    if stage == "closed":
        return ["open", "closed"]
    if stage == "review":
        return ["open", "closed", "review"]
    return ["open"]


# =============================================================================
# UI-КОМПОНЕНТЫ: отдельные секции формы
# =============================================================================
def _render_open_stage(
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
    """Секция открытия сделки (дата, счёт, сетап, риск)."""

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


def _render_closed_stage(
    *,
    trade_key: str,
    visible: bool,
    expanded: bool,
    defaults: Dict[str, Any],
    emotional_defaults: List[str],
) -> Tuple[Dict[str, Any], List[str]]:
    """Секция фиксации результатов после закрытия сделки."""

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
            format_func=lambda value: value if value == RESULT_PLACEHOLDER else _result_label(
                value),
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


def _render_review_stage(
    *,
    trade_key: str,
    visible: bool,
    expanded: bool,
    defaults: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Блок ревью сделки: холодные мысли + оценка."""

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


def _render_charts_block(
    *,
    trade_key: str,
    charts_editor: pd.DataFrame,
) -> pd.DataFrame:
    """Правая колонка с таблицей графиков."""

    st.markdown("#### Charts")
    st.caption(
        "Add a chart link (URL) and optional description. Preview is generated automatically.")
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


def _render_notes_block(
    *,
    trade_key: str,
    observations_editor: pd.DataFrame,
    tag_options: List[str],
) -> pd.DataFrame:
    """Редактор заметок по сделке."""

    st.markdown("#### Trade observations")
    st.caption(
        "Add short observations for the trade. You can keep multiple notes.")
    return st.data_editor(
        observations_editor,
        hide_index=True,
        key=f"tm_observations_{trade_key}",
        num_rows="dynamic",
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


def _render_header_actions(trade_key: str, *, is_create: bool) -> bool:
    """Кнопки действий в шапке (submit / save)."""

    label = "Create trade" if is_create else "Save changes"
    return st.button(
        label,
        type="primary",
        key=f"tm_submit_{trade_key}",
        use_container_width=True,
    )


# =============================================================================
# ОСНОВНОЙ ВХОД: единый trade_manager для создания и редактирования
# =============================================================================


def _format_view_value(value: Optional[Any], placeholder: str = "—") -> str:
    if value is None:
        return placeholder
    if isinstance(value, float):
        formatted = f"{value:.2f}".rstrip('0').rstrip('.')
        return formatted or '0'
    text_value = str(value).strip()
    return text_value or placeholder


def _render_view_tab(
    trade: Dict[str, Any],
    trade_notes: List[Dict[str, Any]],
    trade_charts: List[Dict[str, Any]],
    *,
    accounts: Dict[str, Optional[int]],
    setups: Dict[str, Optional[int]],
    analyses: Dict[str, Optional[int]],
) -> None:
    st.markdown('#### Trade overview')
    summary_col1, summary_col2 = st.columns(2)
    summary_col1.markdown(
        f"**Status:** {_state_label(trade.get('state')) or '—'}")
    summary_col1.markdown(
        f"**Result:** {_result_label(trade.get('result')) or '—'}")
    summary_col1.markdown(
        f"**Date:** {_format_view_value(trade.get('date_local'))}")
    summary_col1.markdown(
        f"**Time:** {_format_view_value(trade.get('time_local'))}")

    summary_col2.markdown(
        f"**Account:** {_current_label(accounts, trade.get('account_id')) if trade.get('account_id') else '—'}"
    )
    summary_col2.markdown(
        f"**Setup:** {_current_label(setups, trade.get('setup_id')) if trade.get('setup_id') else '—'}"
    )
    summary_col2.markdown(
        f"**Analysis:** {_current_label(analyses, trade.get('analysis_id')) if trade.get('analysis_id') else '—'}"
    )

    st.divider()
    st.markdown('#### After close')
    close_col1, close_col2 = st.columns(2)
    close_col1.metric('Net PnL', _format_view_value(trade.get('net_pnl')))
    close_col1.metric('R:R', _format_view_value(trade.get('risk_reward')))
    close_col2.metric('Reward %', _format_view_value(
        trade.get('reward_percent')))
    emotions = parse_emotional_problems(trade.get('emotional_problems'))
    close_col2.metric('Emotions', ', '.join(emotions) if emotions else '—')

    st.write(
        f"**Hot thoughts:** {_format_view_value(trade.get('hot_thoughts'))}")

    st.divider()
    st.markdown('#### Review')
    st.write(
        f"**Cold thoughts:** {_format_view_value(trade.get('cold_thoughts'))}")
    st.write(f"**Estimation:** {_format_view_value(trade.get('estimation'))}")

    st.divider()
    st.markdown('#### Charts')
    if not trade_charts:
        st.caption('Charts not attached')
    else:
        for idx, chart in enumerate(trade_charts, start=1):
            url = chart.get('chart_url') or '—'
            desc = chart.get('description') or chart.get('title') or ''
            st.markdown(f"{idx}. [{url}]({url}) — {desc}")

    st.divider()
    st.markdown('#### Notes')
    if not trade_notes:
        st.caption('No observations yet')
    else:
        for note in trade_notes:
            title = note.get(
                'title') or f"Note #{note.get('id') or ''}".strip()
            with st.expander(title):
                st.write(note.get('body') or '—')
                tags = _split_tags(note.get('tags'))
                st.caption(f"Tags: {', '.join(tags) if tags else '—'}")


def render_trade_manager(
    trade: Optional[Dict[str, Any]],
    *,
    mode: str = 'edit',
    context: str = 'default',
    default_tab: str = 'View',
) -> None:
    if mode not in {'edit', 'create'}:
        raise ValueError("mode должен быть 'edit' или 'create'")

    trade = trade or {}
    trade_id = trade.get('id')
    trade_key = str(trade_id or context)
    is_create = (mode == 'create') and trade_id is None

    # --- Справочные списки (счета / сетапы / анализы) ---
    accounts = _option_with_placeholder(
        list_accounts(),
        placeholder='— Account not selected —',
        formatter=lambda acc: f"{acc['name']} (#{acc['id']})",
    )
    setups = _option_with_placeholder(
        list_setups(),
        placeholder='— Setup not selected —',
        formatter=lambda setup: f"{setup['name']} (#{setup['id']})",
    )
    analyses = _option_with_placeholder(
        list_analysis(),
        placeholder='— Analysis not linked —',
        formatter=lambda analysis: f"{analysis.get('date_local') or 'No date'} · {analysis.get('asset') or '—'} (#{analysis['id']})",
    )
    account_labels = list(accounts.keys())
    setup_labels = list(setups.keys())
    analysis_labels = list(analyses.keys())

    date_value = _parse_date_value(trade.get('date_local'))
    time_value = _parse_time_value(trade.get('time_local'))
    account_label = _current_label(accounts, trade.get('account_id'))
    analysis_label = _current_label(analyses, trade.get('analysis_id'))
    setup_label = _current_label(setups, trade.get('setup_id'))

    asset_candidates = ASSETS or [trade.get('asset') or '—']
    asset_default = trade.get('asset') if trade.get(
        'asset') in asset_candidates else asset_candidates[0]
    assets = asset_candidates if asset_default in asset_candidates else [
        asset_default] + asset_candidates

    emotional_defaults = parse_emotional_problems(
        trade.get('emotional_problems'))
    closed_defaults = {
        'result': trade.get('result') or RESULT_PLACEHOLDER,
        'net_pnl': trade.get('net_pnl') or 0.0,
        'risk_reward': trade.get('risk_reward') or 0.0,
        'reward_percent': trade.get('reward_percent') or 0.0,
        'hot_thoughts': trade.get('hot_thoughts') or '',
    }
    review_defaults = {
        'cold_thoughts': trade.get('cold_thoughts') or '',
        'estimation': trade.get('estimation') or 0,
    }
    open_defaults = {
        'date': date_value,
        'time': time_value,
        'account_label': account_label,
        'asset': asset_default,
        'analysis_label': analysis_label,
        'setup_label': setup_label,
        'risk_pct': float(trade.get('risk_pct') or 1.0),
    }

    # --- Коллекции заметок и графиков ---
    if is_create or not trade_id:
        trade_notes: List[Dict[str, Any]] = []
        trade_charts: List[Dict[str, Any]] = []
    else:
        trade_notes = list_notes_for_trade(trade_id)
        trade_charts = list_charts_for_trade(trade_id)

    observations_df = _notes_dataframe(trade_notes)
    existing_note_ids: Set[int] = {
        int(note['id']) for note in trade_notes if note.get('id') is not None
    }
    tag_options = sorted(
        {tag for tags in observations_df['tags'].tolist() for tag in tags})

    charts_df = _charts_dataframe(trade_charts)
    charts_state_key = f"tm_charts_state_{trade_key}"
    if charts_state_key not in st.session_state:
        st.session_state[charts_state_key] = charts_df.copy()
    charts_editor = st.session_state[charts_state_key]

    current_state = trade.get('state') or 'open'
    if is_create and current_state not in CREATE_ALLOWED_STATUSES:
        current_state = CREATE_ALLOWED_STATUSES[0]

    default_tab = (default_tab or 'Options').lower()
    # --- Табы Options/View (View скрыт, пока нет созданной сделки) ---
    if is_create:
        tab_labels = ['Options']
    else:
        tab_labels = ['Options', 'View']

    tabs = st.tabs(tab_labels)
    tab_map = {label: tab for label, tab in zip(tab_labels, tabs)}

    submitted = False
    selected_state = current_state
    closed_inputs: Dict[str, Any] = {}
    review_inputs: Optional[Dict[str, Any]] = None
    open_values = open_defaults.copy()
    observations_editor = observations_df.copy()

    # --- Вкладка Options: основной редактор ---
    with tab_map['Options']:
        header_container = st.container(border=True)
        with header_container:
            status_col, _, actions_col = st.columns(
                [0.2, 0.3, 0.5],
                gap='large',
                vertical_alignment='bottom',
            )
            with status_col:
                allowed_states = CREATE_ALLOWED_STATUSES if is_create else _allowed_statuses(
                    current_state)
                current_state = current_state if current_state in allowed_states else allowed_states[
                    0]
                selected_state = st.selectbox(
                    'Trade status',
                    allowed_states,
                    index=allowed_states.index(current_state),
                    help='Statuses move sequentially similar to Jira.',
                    format_func=_state_label,
                    key=f"tm_status_{trade_key}",
                )
            with actions_col:
                submitted = _render_header_actions(
                    trade_key, is_create=is_create)

        visible_stages = _visible_stages(selected_state)
        expanded_stage = STATUS_STAGE.get(selected_state, 'open')

        col1, col2 = st.columns([1, 2])
        with col1:
            open_values = _render_open_stage(
                trade_key=trade_key,
                visible='open' in visible_stages,
                expanded=(expanded_stage == 'open'),
                defaults=open_defaults,
                account_labels=account_labels,
                assets=assets,
                analysis_labels=analysis_labels,
                setup_labels=setup_labels,
            )

            closed_inputs, emotional_defaults = _render_closed_stage(
                trade_key=trade_key,
                visible='closed' in visible_stages,
                expanded=(expanded_stage == 'closed'),
                defaults=closed_defaults,
                emotional_defaults=emotional_defaults,
            )

            review_inputs = _render_review_stage(
                trade_key=trade_key,
                visible='review' in visible_stages,
                expanded=(expanded_stage == 'review'),
                defaults=review_defaults,
            )

        with col2:
            charts_editor = _render_charts_block(
                trade_key=trade_key,
                charts_editor=charts_editor,
            )
            st.session_state[charts_state_key] = charts_editor

            observations_editor = _render_notes_block(
                trade_key=trade_key,
                observations_editor=observations_df,
                tag_options=tag_options,
            )

    # --- Вкладка View: только чтение ---
    if not is_create:
        with tab_map['View']:
            _render_view_tab(
                trade,
                trade_notes,
                trade_charts,
                accounts=accounts,
                setups=setups,
                analyses=analyses,
            )

    # --- Ожидаем клика по кнопке ---
    if not submitted:
        return

    # --- Мини-валидации обязательных блоков ---
    errors: List[str] = []
    if selected_state in ('closed', 'reviewed'):
        if not closed_inputs:
            errors.append('Fill in the “After close” block.')
        else:
            if closed_inputs['result'] == RESULT_PLACEHOLDER:
                errors.append('Select the trade result.')
            if closed_inputs['net_pnl'] is None:
                errors.append('Provide Net PnL.')
    if errors:
        for err in errors:
            st.error(err)
        return

    # --- Сбор payload для БД ---
    payload: Dict[str, Any] = {
        'date_local': open_values['date'].isoformat(),
        'time_local': open_values['time'].strftime('%H:%M:%S'),
        'account_id': accounts[open_values['account_label']],
        'asset': open_values['asset'],
        'analysis_id': analyses[open_values['analysis_label']],
        'setup_id': setups[open_values['setup_label']],
        'risk_pct': float(open_values['risk_pct']),
        'state': selected_state,
    }

    if closed_inputs:
        payload.update({
            'result': None if closed_inputs['result'] == RESULT_PLACEHOLDER else closed_inputs['result'],
            'net_pnl': float(closed_inputs['net_pnl']),
            'risk_reward': float(closed_inputs['risk_reward']),
            'reward_percent': float(closed_inputs['reward_percent']),
            'hot_thoughts': closed_inputs['hot_thoughts'].strip() or None,
            'emotional_problems': emotional_defaults,
        })
    else:
        payload.update({
            'result': None,
            'net_pnl': None,
            'risk_reward': None,
            'reward_percent': None,
            'hot_thoughts': None,
            'emotional_problems': None,
        })

    if review_inputs:
        payload.update({
            'cold_thoughts': review_inputs['cold_thoughts'].strip() or None,
            'estimation': int(review_inputs['estimation']),
        })
    else:
        payload.update({
            'cold_thoughts': None if selected_state != 'reviewed' else trade.get('cold_thoughts'),
            'estimation': None if selected_state != 'reviewed' else trade.get('estimation'),
        })

    if selected_state in ('closed', 'reviewed') and not trade.get('closed_at_utc'):
        payload['closed_at_utc'] = datetime.utcnow().strftime(
            '%Y-%m-%dT%H:%M:%S')

    note_records = _prepare_note_records(
        observations_editor, existing_note_ids)
    chart_records = _prepare_chart_records(charts_editor)

    # --- Сохранение: создаём новую запись или обновляем существующую ---
    try:
        if is_create:
            new_trade_id = create_trade(payload)
            replace_trade_notes(new_trade_id, note_records)
            replace_trade_charts(new_trade_id, chart_records)
            st.session_state[f'tm_{context}_created_id'] = new_trade_id
            st.session_state['selected_trade_id'] = new_trade_id
            st.session_state.pop(charts_state_key, None)
            st.success('Сделка создана.')
        else:
            if trade_id is None:
                raise ValueError(
                    'Не выбран trade_id для режима редактирования')
            update_trade(trade_id, payload)
            replace_trade_notes(trade_id, note_records)
            replace_trade_charts(trade_id, chart_records)
            st.session_state.pop(charts_state_key, None)
            st.success('Trade updated.')
        st.rerun()
    except Exception as exc:
        st.error(f'Failed to persist the trade: {exc}')


def reset_trade_manager_context(context: str, *, trade_id: Optional[int] = None) -> None:
    """Сбрасываем связанные с менеджером ключи session_state."""

    prefix = f'tm_{context}'
    st.session_state.pop(f'{prefix}_created_id', None)
    st.session_state.pop(f'tm_charts_state_{context}', None)
    if trade_id is not None:
        st.session_state.pop(f'tm_charts_state_{trade_id}', None)
