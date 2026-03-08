# tests/test_helpers.py — Unit tests for helpers module
from datetime import date, datetime, time

import pytest

from helpers import (
    calculate_trade_result,
    format_local_date,
    format_local_time,
    format_number,
    get_excerpt,
    is_loss_rr,
    is_win_rr,
    parse_date,
    parse_time,
    safe_choice_index,
    to_option_format,
)
from config import BE_THRESHOLD


class TestCalculateTradeResult:
    """Boundary and edge case tests for calculate_trade_result()."""

    # --- is_missed takes priority ---
    def test_missed_returns_miss_regardless_of_rr(self):
        assert calculate_trade_result(5.0, is_missed=1) == "Miss"

    def test_missed_with_none_rr(self):
        assert calculate_trade_result(None, is_missed=1) == "Miss"

    # --- None risk_reward ---
    def test_none_rr_not_missed_returns_empty(self):
        assert calculate_trade_result(None, is_missed=0) == ""

    # --- Win ---
    def test_rr_above_threshold_is_win(self):
        assert calculate_trade_result(BE_THRESHOLD + 0.01, is_missed=0) == "Win"

    def test_rr_well_above_threshold_is_win(self):
        assert calculate_trade_result(3.0, is_missed=0) == "Win"

    # --- Loss ---
    def test_rr_below_negative_threshold_is_loss(self):
        assert calculate_trade_result(-BE_THRESHOLD - 0.01, is_missed=0) == "Loss"

    def test_rr_well_below_negative_threshold_is_loss(self):
        assert calculate_trade_result(-3.0, is_missed=0) == "Loss"

    # --- BE (boundary: exactly on threshold is BE, not Win/Loss) ---
    def test_rr_exactly_threshold_is_be(self):
        assert calculate_trade_result(BE_THRESHOLD, is_missed=0) == "BE"

    def test_rr_exactly_negative_threshold_is_be(self):
        assert calculate_trade_result(-BE_THRESHOLD, is_missed=0) == "BE"

    def test_rr_zero_is_be(self):
        assert calculate_trade_result(0.0, is_missed=0) == "BE"

    def test_rr_just_below_threshold_is_be(self):
        assert calculate_trade_result(BE_THRESHOLD - 0.001, is_missed=0) == "BE"

    def test_rr_just_above_negative_threshold_is_be(self):
        assert calculate_trade_result(-BE_THRESHOLD + 0.001, is_missed=0) == "BE"


class TestIsWinRr:
    def test_above_threshold(self):
        assert is_win_rr(BE_THRESHOLD + 0.01) is True

    def test_exactly_threshold_not_win(self):
        assert is_win_rr(BE_THRESHOLD) is False

    def test_none_not_win(self):
        assert is_win_rr(None) is False

    def test_negative_not_win(self):
        assert is_win_rr(-1.0) is False


class TestIsLossRr:
    def test_below_negative_threshold(self):
        assert is_loss_rr(-BE_THRESHOLD - 0.01) is True

    def test_exactly_negative_threshold_not_loss(self):
        assert is_loss_rr(-BE_THRESHOLD) is False

    def test_none_not_loss(self):
        assert is_loss_rr(None) is False

    def test_positive_not_loss(self):
        assert is_loss_rr(1.0) is False


class TestParseDate:
    def test_string_iso(self):
        assert parse_date("2026-01-15") == date(2026, 1, 15)

    def test_string_dot_format(self):
        assert parse_date("15.01.2026") == date(2026, 1, 15)

    def test_date_object_returned_as_is(self):
        d = date(2026, 1, 15)
        assert parse_date(d) == d

    def test_datetime_returns_date_part(self):
        dt = datetime(2026, 1, 15, 10, 30)
        assert parse_date(dt) == date(2026, 1, 15)

    def test_none_returns_none(self):
        assert parse_date(None) is None

    def test_invalid_string_returns_none(self):
        assert parse_date("not-a-date") is None


class TestParseTime:
    def test_string_hhmmss(self):
        assert parse_time("10:30:00") == time(10, 30, 0)

    def test_string_hhmm(self):
        assert parse_time("10:30") == time(10, 30)

    def test_time_object_returned_as_is(self):
        t = time(10, 30)
        assert parse_time(t) == t

    def test_none_returns_none(self):
        assert parse_time(None) is None

    def test_invalid_string_returns_none(self):
        assert parse_time("not-a-time") is None


class TestToOptionFormat:
    def test_basic(self):
        items = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        result = to_option_format(items, formatter=lambda x: x["name"])
        assert result == [{"label": "A", "value": 1}, {"label": "B", "value": 2}]

    def test_skips_items_with_none_id(self):
        items = [{"id": None, "name": "skip"}, {"id": 1, "name": "keep"}]
        result = to_option_format(items, formatter=lambda x: x["name"])
        assert len(result) == 1
        assert result[0]["value"] == 1

    def test_empty_list(self):
        assert to_option_format([], formatter=lambda x: x["name"]) == []


class TestSafeChoiceIndex:
    def test_value_present(self):
        assert safe_choice_index(["A", "B", "C"], "B") == 1

    def test_value_missing(self):
        assert safe_choice_index(["A", "B"], "Z") is None

    def test_none_value(self):
        assert safe_choice_index(["A", "B"], None) is None




class TestFormatLocalDate:
    def test_none_returns_empty(self):
        assert format_local_date(None) == ""

    def test_date_object(self):
        assert format_local_date(date(2026, 1, 5)) == "05.01.2026"

    def test_datetime_object(self):
        assert format_local_date(datetime(2026, 1, 5, 10, 0)) == "05.01.2026"

    def test_iso_string(self):
        assert format_local_date("2026-01-05") == "05.01.2026"

    def test_invalid_string_returned_as_is(self):
        assert format_local_date("not-a-date") == "not-a-date"


class TestFormatLocalTime:
    def test_none_returns_empty(self):
        assert format_local_time(None) == ""

    def test_time_object(self):
        assert format_local_time(time(10, 30)) == "10:30"

    def test_iso_datetime_string(self):
        assert format_local_time("2026-01-01T10:30:00") == "10:30"

    def test_hhmm_string(self):
        assert format_local_time("10:30") == "10:30"

    def test_short_string_less_than_5_chars(self):
        assert format_local_time("1:3") == "1:3"


class TestFormatNumber:
    def test_none_returns_empty(self):
        assert format_number(None) == ""

    def test_float(self):
        assert format_number(1.5) == "1.50"

    def test_int(self):
        assert format_number(3) == "3.00"

    def test_negative(self):
        assert format_number(-2.5) == "-2.50"

    def test_non_numeric_string(self):
        assert format_number("abc") == "abc"


class TestGetExcerpt:
    def test_short_text_returned_as_is(self):
        assert get_excerpt("Hello", 10) == "Hello"

    def test_long_text_truncated_with_ellipsis(self):
        result = get_excerpt("Hello, world!", 8)
        assert result.endswith("...")
        assert len(result) == 8

    def test_empty_string_returns_empty(self):
        assert get_excerpt("", 10) == ""

    def test_none_returns_empty(self):
        assert get_excerpt(None, 10) == ""

    def test_limit_le_3_no_ellipsis(self):
        assert get_excerpt("Hello", 2) == "He"

    def test_exactly_at_limit(self):
        assert get_excerpt("Hello", 5) == "Hello"
