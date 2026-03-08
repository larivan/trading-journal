# tests/test_trades.py — Unit tests for trades module
import json
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
def trade_dependencies(test_user):
    """Create required dependencies for trades."""
    account_id = create_account(test_user, name="Test Account", starting_balance=10000.0)
    setup_id = create_setup(test_user, name="Test Setup")
    analysis_id = add_analysis(test_user, {"date_local": "2026-02-01"})
    return {
        "account_id": account_id,
        "setup_id": setup_id,
        "analysis_id": analysis_id,
        "user_id": test_user,
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
        "is_missed": 0,
        "net_pnl": 150.0,
        "risk_reward": 2.5,
    }
    data.update(overrides)
    return data


class TestCreateTrade:
    def test_create_trade_basic(self, trade_dependencies):
        """Test creating a basic trade."""
        user_id = trade_dependencies["user_id"]
        data = make_trade_data(trade_dependencies)
        trade_id = create_trade(user_id, data)

        assert trade_id is not None
        assert trade_id > 0

    def test_create_trade_all_fields(self, trade_dependencies):
        """Test creating trade with all fields."""
        user_id = trade_dependencies["user_id"]
        data = make_trade_data(
            trade_dependencies,
            risk_pct=1.0,
            reward_percent=2.5,
            is_correct=1,
        )
        trade_id = create_trade(user_id, data)

        trade = get_trade_by_id(trade_id, user_id)
        assert trade["risk_pct"] == 1.0
        assert trade["is_correct"] == 1

    def test_create_trade_empty_raises(self, trade_dependencies):
        """Create trade with empty dict raises ValueError."""
        user_id = trade_dependencies["user_id"]
        with pytest.raises(ValueError, match="No data"):
            create_trade(user_id, {})


class TestTradeType:
    def test_trade_type(self, trade_dependencies):
        """Test creating trade with trade_type field."""
        user_id = trade_dependencies["user_id"]
        trade_id = create_trade(user_id, make_trade_data(
            trade_dependencies, trade_type="Intraday"
        ))
        trade = get_trade_by_id(trade_id, user_id)
        assert trade["trade_type"] == "Intraday"

    def test_trade_type_swing(self, trade_dependencies):
        """Test creating trade with Swing type."""
        user_id = trade_dependencies["user_id"]
        trade_id = create_trade(user_id, make_trade_data(
            trade_dependencies, trade_type="Swing"
        ))
        trade = get_trade_by_id(trade_id, user_id)
        assert trade["trade_type"] == "Swing"


class TestMistakeTypes:
    def test_mistake_types_saved_as_json(self, trade_dependencies):
        """Test that mistake_types list is serialized and deserialized correctly."""
        user_id = trade_dependencies["user_id"]
        mistakes = ["Early entry", "Wrong stop placement"]
        trade_id = create_trade(user_id, make_trade_data(
            trade_dependencies,
            is_correct=0,
            mistake_types=mistakes,
        ))
        trade = get_trade_by_id(trade_id, user_id)
        # mistake_types is stored as JSON string in DB
        stored = trade.get("mistake_types")
        assert stored is not None
        parsed = json.loads(stored) if isinstance(stored, str) else stored
        assert parsed == mistakes

    def test_mistake_types_empty_list(self, trade_dependencies):
        """Test saving empty mistake_types."""
        user_id = trade_dependencies["user_id"]
        trade_id = create_trade(user_id, make_trade_data(
            trade_dependencies, mistake_types=[]
        ))
        trade = get_trade_by_id(trade_id, user_id)
        stored = trade.get("mistake_types")
        if stored:
            assert json.loads(stored) == []


class TestComputedStatus:
    def test_status_open(self, trade_dependencies):
        """Trade with no net_pnl and no is_missed → Open."""
        user_id = trade_dependencies["user_id"]
        trade_id = create_trade(user_id, make_trade_data(
            trade_dependencies, net_pnl=None, risk_reward=None, is_missed=0
        ))
        trades = list_trades(user_id)
        t = next(x for x in trades if x["id"] == trade_id)
        assert t["status"] == "Open"

    def test_status_outcome(self, trade_dependencies):
        """Trade with net_pnl set → Outcome."""
        user_id = trade_dependencies["user_id"]
        trade_id = create_trade(user_id, make_trade_data(
            trade_dependencies, net_pnl=100.0, is_correct=None
        ))
        trades = list_trades(user_id)
        t = next(x for x in trades if x["id"] == trade_id)
        assert t["status"] == "Outcome"

    def test_status_reviewed(self, trade_dependencies):
        """Trade with is_correct set → Reviewed."""
        user_id = trade_dependencies["user_id"]
        trade_id = create_trade(user_id, make_trade_data(
            trade_dependencies, net_pnl=100.0, is_correct=1
        ))
        trades = list_trades(user_id)
        t = next(x for x in trades if x["id"] == trade_id)
        assert t["status"] == "Reviewed"

    def test_status_missed_outcome(self, trade_dependencies):
        """Missed trade → Outcome (regardless of net_pnl)."""
        user_id = trade_dependencies["user_id"]
        trade_id = create_trade(user_id, make_trade_data(
            trade_dependencies, is_missed=1, net_pnl=None, risk_reward=None
        ))
        trades = list_trades(user_id)
        t = next(x for x in trades if x["id"] == trade_id)
        assert t["status"] == "Outcome"


class TestListTrades:
    def test_list_empty(self, test_user):
        """Test listing when no trades exist."""
        trades = list_trades(test_user)
        assert trades == []

    def test_list_trades(self, trade_dependencies):
        """Test listing multiple trades."""
        user_id = trade_dependencies["user_id"]
        for i in range(3):
            create_trade(user_id, make_trade_data(
                trade_dependencies,
                date_local=f"2026-02-0{i+1}",
            ))

        trades = list_trades(user_id)
        assert len(trades) == 3

    def test_filter_by_account(self, test_user):
        """Test filtering trades by account."""
        user_id = test_user
        acc1 = create_account(user_id, name="Account 1", starting_balance=10000.0)
        acc2 = create_account(user_id, name="Account 2", starting_balance=10000.0)
        setup_id = create_setup(user_id, name="Setup")
        analysis_id = add_analysis(user_id, {"date_local": "2026-02-01"})

        deps1 = {"account_id": acc1, "setup_id": setup_id, "analysis_id": analysis_id, "user_id": user_id}
        deps2 = {"account_id": acc2, "setup_id": setup_id, "analysis_id": analysis_id, "user_id": user_id}

        create_trade(user_id, make_trade_data(deps1))
        create_trade(user_id, make_trade_data(deps1))
        create_trade(user_id, make_trade_data(deps2))

        trades = list_trades(user_id, {"account_id": acc1})
        assert len(trades) == 2

    def test_filter_by_date_range(self, trade_dependencies):
        """Test filtering trades by date range."""
        user_id = trade_dependencies["user_id"]
        create_trade(user_id, make_trade_data(trade_dependencies, date_local="2026-01-15"))
        create_trade(user_id, make_trade_data(trade_dependencies, date_local="2026-02-01"))
        create_trade(user_id, make_trade_data(trade_dependencies, date_local="2026-02-15"))

        trades = list_trades(user_id, {
            "date_from": "2026-02-01",
            "date_to": "2026-02-10",
        })
        assert len(trades) == 1


class TestFilterByResult:
    """Tests for list_trades() result filter using BE_THRESHOLD logic."""

    @pytest.fixture
    def result_deps(self, test_user):
        user_id = test_user
        account_id = create_account(user_id, name="Acc", starting_balance=10000.0)
        setup_id = create_setup(user_id, name="S")
        analysis_id = add_analysis(user_id, {"date_local": "2026-01-01"})
        return {"account_id": account_id, "setup_id": setup_id, "analysis_id": analysis_id, "user_id": user_id}

    def _make(self, deps, **kw):
        return make_trade_data(deps, **kw)

    def test_filter_win(self, result_deps):
        user_id = result_deps["user_id"]
        create_trade(user_id, self._make(result_deps, risk_reward=2.0, is_missed=0))
        create_trade(user_id, self._make(result_deps, risk_reward=-1.0, is_missed=0, date_local="2026-01-02"))
        create_trade(user_id, self._make(result_deps, risk_reward=0.0, is_missed=0, date_local="2026-01-03"))

        trades = list_trades(user_id, {"result": "Win"})
        assert len(trades) == 1
        assert trades[0]["risk_reward"] == 2.0

    def test_filter_loss(self, result_deps):
        user_id = result_deps["user_id"]
        create_trade(user_id, self._make(result_deps, risk_reward=2.0, is_missed=0))
        create_trade(user_id, self._make(result_deps, risk_reward=-1.0, is_missed=0, date_local="2026-01-02"))

        trades = list_trades(user_id, {"result": "Loss"})
        assert len(trades) == 1
        assert trades[0]["risk_reward"] == -1.0

    def test_filter_be(self, result_deps):
        user_id = result_deps["user_id"]
        create_trade(user_id, self._make(result_deps, risk_reward=0.0, is_missed=0))
        create_trade(user_id, self._make(result_deps, risk_reward=2.0, is_missed=0, date_local="2026-01-02"))

        trades = list_trades(user_id, {"result": "BE"})
        assert len(trades) == 1
        assert trades[0]["risk_reward"] == 0.0

    def test_filter_miss(self, result_deps):
        user_id = result_deps["user_id"]
        create_trade(user_id, self._make(result_deps, is_missed=1, risk_reward=0.0))
        create_trade(user_id, self._make(result_deps, is_missed=0, risk_reward=2.0, date_local="2026-01-02"))

        trades = list_trades(user_id, {"result": "Miss"})
        assert len(trades) == 1
        assert trades[0]["is_missed"] == 1


class TestGetTrade:
    def test_get_existing(self, trade_dependencies):
        """Test getting an existing trade."""
        user_id = trade_dependencies["user_id"]
        trade_id = create_trade(user_id, make_trade_data(trade_dependencies))
        trade = get_trade_by_id(trade_id, user_id)

        assert trade is not None
        assert trade["asset"] == "EUR/USD"
        assert trade["session"] == "LOKZ"

    def test_get_nonexistent(self, test_user):
        """Test getting a non-existent trade."""
        trade = get_trade_by_id(99999, test_user)
        assert trade is None


class TestUpdateTrade:
    def test_update_pnl(self, trade_dependencies):
        """Test updating trade PnL."""
        user_id = trade_dependencies["user_id"]
        trade_id = create_trade(user_id, make_trade_data(trade_dependencies))
        update_trade(trade_id, user_id, {"net_pnl": 200.0})

        trade = get_trade_by_id(trade_id, user_id)
        assert trade["net_pnl"] == 200.0

    def test_update_multiple_fields(self, trade_dependencies):
        """Test updating multiple fields."""
        user_id = trade_dependencies["user_id"]
        trade_id = create_trade(user_id, make_trade_data(trade_dependencies))
        update_trade(trade_id, user_id, {
            "is_correct": 0,
            "trade_type": "Swing",
        })

        trade = get_trade_by_id(trade_id, user_id)
        assert trade["is_correct"] == 0
        assert trade["trade_type"] == "Swing"

    def test_update_nonexistent_raises(self, test_user):
        """Update invalid trade ID raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            update_trade(99999, test_user, {"net_pnl": 100.0})


class TestFKViolation:
    def test_invalid_account_id_raises(self, test_user):
        """create_trade() with non-existent account_id raises an integrity error."""
        import sqlite3
        payload = {
            "local_tz": "UTC+3",
            "date_local": "2026-01-01",
            "time_local": "10:00:00",
            "account_id": 99999,
            "asset": "EUR/USD",
            "session": "LOKZ",
            "is_missed": 0,
        }
        with pytest.raises((sqlite3.IntegrityError, Exception)):
            create_trade(test_user, payload)


class TestDeleteTrade:
    def test_delete_trade(self, trade_dependencies):
        """Test deleting a trade."""
        user_id = trade_dependencies["user_id"]
        trade_id = create_trade(user_id, make_trade_data(trade_dependencies))
        delete_trade(trade_id, user_id)

        assert get_trade_by_id(trade_id, user_id) is None

    def test_delete_nonexistent_raises(self, test_user):
        """Delete invalid trade ID raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            delete_trade(99999, test_user)
