# tests/test_trades.py — Unit tests for trades module
import pytest
from db.trades import (
    create_trade,
    list_trades,
    get_trade_by_id,
    update_trade,
    delete_trade,
)
from db.accounts import create_account
from db.setups import create_setup
from db.analysis import add_analysis


@pytest.fixture
def trade_dependencies(temp_db):
    """Create required dependencies for trades."""
    account_id = create_account(name="Test Account", starting_balance=10000.0)
    setup_id = create_setup(name="Test Setup")
    analysis_id = add_analysis({"date_local": "2026-02-01"})
    return {
        "account_id": account_id,
        "setup_id": setup_id,
        "analysis_id": analysis_id,
    }


def make_trade_data(deps, **overrides):
    """Helper to create trade data dict."""
    data = {
        "local_tz": "UTC+3",
        "date_local": "2026-02-01",
        "time_local": "10:30:00",
        "account_id": deps["account_id"],
        "setup_id": deps["setup_id"],
        "analysis_id": deps["analysis_id"],
        "asset": "EUR/USD",
        "session": "LOKZ",
        "state": "Reviewed",
        "is_missed": 0,
        "net_pnl": 150.0,
        "risk_reward": 2.5,
    }
    data.update(overrides)
    return data


class TestCreateTrade:
    def test_create_trade_basic(self, trade_dependencies):
        """Test creating a basic trade."""
        data = make_trade_data(trade_dependencies)
        trade_id = create_trade(data)
        
        assert trade_id is not None
        assert trade_id > 0

    def test_create_trade_all_fields(self, trade_dependencies):
        """Test creating trade with all fields."""
        data = make_trade_data(
            trade_dependencies,
            risk_pct=1.0,
            reward_percent=2.5,
            estimation=1,
            emotional_problems="None",
            hot_thoughts="Followed plan",
            cold_thoughts="Good execution",
        )
        trade_id = create_trade(data)
        
        trade = get_trade_by_id(trade_id)
        assert trade["risk_pct"] == 1.0
        assert trade["estimation"] == 1
        assert trade["hot_thoughts"] == "Followed plan"

    def test_create_trade_empty_raises(self, trade_dependencies):
        """Create trade with empty dict raises ValueError."""
        with pytest.raises(ValueError, match="No data"):
            create_trade({})


class TestListTrades:
    def test_list_empty(self, temp_db):
        """Test listing when no trades exist."""
        trades = list_trades()
        assert trades == []

    def test_list_trades(self, trade_dependencies):
        """Test listing multiple trades."""
        for i in range(3):
            create_trade(make_trade_data(
                trade_dependencies,
                date_local=f"2026-02-0{i+1}",
            ))
        
        trades = list_trades()
        assert len(trades) == 3

    def test_filter_by_account(self, temp_db):
        """Test filtering trades by account."""
        acc1 = create_account(name="Account 1", starting_balance=10000.0)
        acc2 = create_account(name="Account 2", starting_balance=10000.0)
        setup_id = create_setup(name="Setup")
        analysis_id = add_analysis({"date_local": "2026-02-01"})
        
        deps1 = {"account_id": acc1, "setup_id": setup_id, "analysis_id": analysis_id}
        deps2 = {"account_id": acc2, "setup_id": setup_id, "analysis_id": analysis_id}
        
        create_trade(make_trade_data(deps1))
        create_trade(make_trade_data(deps1))
        create_trade(make_trade_data(deps2))
        
        trades = list_trades({"account_id": acc1})
        assert len(trades) == 2

    def test_filter_by_date_range(self, trade_dependencies):
        """Test filtering trades by date range."""
        create_trade(make_trade_data(trade_dependencies, date_local="2026-01-15"))
        create_trade(make_trade_data(trade_dependencies, date_local="2026-02-01"))
        create_trade(make_trade_data(trade_dependencies, date_local="2026-02-15"))
        
        trades = list_trades({
            "date_from": "2026-02-01",
            "date_to": "2026-02-10",
        })
        assert len(trades) == 1


class TestFilterByResult:
    """Tests for list_trades() result filter using BE_THRESHOLD logic."""

    @pytest.fixture
    def result_deps(self, temp_db):
        account_id = create_account(name="Acc", starting_balance=10000.0)
        setup_id = create_setup(name="S")
        analysis_id = add_analysis({"date_local": "2026-01-01"})
        return {"account_id": account_id, "setup_id": setup_id, "analysis_id": analysis_id}

    def _make(self, deps, **kw):
        return make_trade_data(deps, **kw)

    def test_filter_win(self, result_deps):
        create_trade(self._make(result_deps, risk_reward=2.0, is_missed=0))
        create_trade(self._make(result_deps, risk_reward=-1.0, is_missed=0, date_local="2026-01-02"))
        create_trade(self._make(result_deps, risk_reward=0.0, is_missed=0, date_local="2026-01-03"))

        trades = list_trades({"result": "Win"})
        assert len(trades) == 1
        assert trades[0]["risk_reward"] == 2.0

    def test_filter_loss(self, result_deps):
        create_trade(self._make(result_deps, risk_reward=2.0, is_missed=0))
        create_trade(self._make(result_deps, risk_reward=-1.0, is_missed=0, date_local="2026-01-02"))

        trades = list_trades({"result": "Loss"})
        assert len(trades) == 1
        assert trades[0]["risk_reward"] == -1.0

    def test_filter_be(self, result_deps):
        create_trade(self._make(result_deps, risk_reward=0.0, is_missed=0))
        create_trade(self._make(result_deps, risk_reward=2.0, is_missed=0, date_local="2026-01-02"))

        trades = list_trades({"result": "BE"})
        assert len(trades) == 1
        assert trades[0]["risk_reward"] == 0.0

    def test_filter_miss(self, result_deps):
        create_trade(self._make(result_deps, is_missed=1, risk_reward=0.0))
        create_trade(self._make(result_deps, is_missed=0, risk_reward=2.0, date_local="2026-01-02"))

        trades = list_trades({"result": "Miss"})
        assert len(trades) == 1
        assert trades[0]["is_missed"] == 1


class TestGetTrade:
    def test_get_existing(self, trade_dependencies):
        """Test getting an existing trade."""
        trade_id = create_trade(make_trade_data(trade_dependencies))
        trade = get_trade_by_id(trade_id)
        
        assert trade is not None
        assert trade["asset"] == "EUR/USD"
        assert trade["session"] == "LOKZ"

    def test_get_nonexistent(self, temp_db):
        """Test getting a non-existent trade."""
        trade = get_trade_by_id(99999)
        assert trade is None


class TestUpdateTrade:
    def test_update_pnl(self, trade_dependencies):
        """Test updating trade PnL."""
        trade_id = create_trade(make_trade_data(trade_dependencies))
        update_trade(trade_id, {"net_pnl": 200.0})
        
        trade = get_trade_by_id(trade_id)
        assert trade["net_pnl"] == 200.0

    def test_update_multiple_fields(self, trade_dependencies):
        """Test updating multiple fields."""
        trade_id = create_trade(make_trade_data(trade_dependencies))
        update_trade(trade_id, {
            "state": "Open",
            "estimation": 0,
            "cold_thoughts": "Updated thoughts",
        })
        
        trade = get_trade_by_id(trade_id)
        assert trade["state"] == "Open"
        assert trade["estimation"] == 0
        assert trade["cold_thoughts"] == "Updated thoughts"

    def test_update_nonexistent_raises(self, trade_dependencies):
        """Update invalid trade ID raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            update_trade(99999, {"net_pnl": 100.0})


class TestFKViolation:
    def test_invalid_account_id_raises(self, temp_db):
        """create_trade() with non-existent account_id raises an integrity error."""
        import sqlite3
        payload = {
            "local_tz": "UTC+3",
            "date_local": "2026-01-01",
            "time_local": "10:00:00",
            "account_id": 99999,
            "asset": "EUR/USD",
            "session": "LOKZ",
            "state": "Open",
            "is_missed": 0,
        }
        with pytest.raises((sqlite3.IntegrityError, Exception)):
            create_trade(payload)


class TestDeleteTrade:
    def test_delete_trade(self, trade_dependencies):
        """Test deleting a trade."""
        trade_id = create_trade(make_trade_data(trade_dependencies))
        delete_trade(trade_id)
        
        assert get_trade_by_id(trade_id) is None

    def test_delete_nonexistent_raises(self, trade_dependencies):
        """Delete invalid trade ID raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            delete_trade(99999)
