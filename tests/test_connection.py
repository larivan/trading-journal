# tests/test_connection.py — Tests for transaction() context manager
import pytest
from db.connection import transaction, get_conn
from db.trades import create_trade, get_trade_by_id
from db.accounts import create_account
from db.setups import create_setup


@pytest.fixture
def trade_deps(test_user):
    account_id = create_account(test_user, name="Acc", starting_balance=10000.0)
    setup_id = create_setup(test_user, name="S")
    return {"account_id": account_id, "setup_id": setup_id, "user_id": test_user}


def _trade_payload(deps):
    return {
        "local_tz": "UTC+3",
        "date_local": "2026-01-01",
        "time_local": "10:00:00",
        "account_id": deps["account_id"],
        "setup_id": deps["setup_id"],
        "asset": "EUR/USD",
        "session": "LOKZ",
        "state": "Open",
        "is_missed": 0,
    }


class TestTransaction:
    def test_commit_on_success(self, trade_deps):
        """transaction() commits when no exception is raised."""
        user_id = trade_deps["user_id"]
        with transaction() as conn:
            trade_id = create_trade(user_id, _trade_payload(trade_deps), conn=conn)

        assert get_trade_by_id(trade_id, user_id) is not None

    def test_rollback_on_exception(self, trade_deps):
        """transaction() rolls back all changes when an exception is raised."""
        user_id = trade_deps["user_id"]
        trade_id = None
        with pytest.raises(RuntimeError):
            with transaction() as conn:
                trade_id = create_trade(user_id, _trade_payload(trade_deps), conn=conn)
                raise RuntimeError("forced failure")

        assert trade_id is not None
        assert get_trade_by_id(trade_id, user_id) is None

    def test_exception_is_reraised(self, trade_deps):
        """transaction() re-raises the original exception after rollback."""
        with pytest.raises(ValueError, match="test error"):
            with transaction():
                raise ValueError("test error")
