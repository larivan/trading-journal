# tests/test_helpers.py — Unit tests for helpers module
from helpers import calculate_trade_result, is_win_rr, is_loss_rr
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
