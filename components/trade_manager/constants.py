"""Константы и предопределённые значения для трейд-менеджера."""

from typing import Dict, List

# --- Допустимые переходы между статусами сделки ---
STATUS_TRANSITIONS: Dict[str, List[str]] = {
    "open": ["open", "closed", "cancelled"],
    "closed": ["closed", "reviewed"],
    "reviewed": ["reviewed"],
    "cancelled": ["cancelled", "reviewed"],
    "missed": ["missed", "reviewed"],
}

# --- Карта статусов к визуальным стадиям (какие блоки формы показывать) ---
STATUS_STAGE = {
    "open": "open",
    "closed": "closed",
    "reviewed": "review",
    "cancelled": "open",
    "missed": "open",
}

# --- Значение-заглушка для селекта результата ---
RESULT_PLACEHOLDER = "— Not set —"

# --- Статусы, доступные при создании сделки ---
CREATE_ALLOWED_STATUSES = ["open", "missed"]
