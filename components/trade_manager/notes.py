"""Работа с заметками и графиками для трейд-менеджера."""

"""Работа с заметками и графиками для трейд-менеджера."""

from typing import Any, Dict, List, Optional, Set

import pandas as pd


def build_notes_dataframe(notes: List[Dict[str, Any]]) -> pd.DataFrame:
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
    df["tags"] = df["tags"].apply(split_tags)
    return df


def build_charts_dataframe(charts: List[Dict[str, Any]]) -> pd.DataFrame:
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


def split_tags(raw_value: Any) -> List[str]:
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


def serialize_tags(raw_value: Any) -> Optional[str]:
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


def prepare_note_records(editor_df: Optional[pd.DataFrame],
                         existing_ids: Optional[Set[int]] = None) -> List[Dict[str, Any]]:
    if editor_df is None:
        return []
    existing_ids = {
        int(note_id) for note_id in (existing_ids or set()) if note_id is not None
    }
    working_df = editor_df.copy()
    if "id" not in working_df.columns:
        index_label = working_df.index.name or "index"
        working_df = working_df.reset_index().rename(columns={index_label: "id"})
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
            "tags": serialize_tags(row.get("tags")),
        })
    return records


def prepare_chart_records(editor_df: Optional[pd.DataFrame]) -> List[Dict[str, Any]]:
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
