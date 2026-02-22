# tests/test_charts.py — Tests for db/charts.py
import pytest

from db.charts import (
    add_chart,
    get_chart,
    update_chart,
    delete_chart,
    list_charts,
    attach_chart,
    detach_chart,
    attach_chart_to_trade,
    detach_chart_from_trade,
)
from db.trades import create_trade
from db.accounts import create_account


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_account(user_id, conn=None):
    return create_account(user_id, "Test", starting_balance=1000.0, conn=conn)


def _make_trade(user_id, account_id, conn=None):
    return create_trade(user_id, {
        "date_local": "2024-01-01",
        "time_local": "10:00:00",
        "account_id": account_id,
        "asset": "EURUSD",
        "session": "LOKZ",
        "state": "Open",
        "local_tz": "UTC+3",
    }, conn=conn)


# ---------------------------------------------------------------------------
# add_chart / get_chart
# ---------------------------------------------------------------------------

class TestAddGetChart:
    def test_add_chart_returns_id(self, temp_db):
        chart_id = add_chart("https://example.com/chart.png")
        assert isinstance(chart_id, int)
        assert chart_id > 0

    def test_add_chart_with_caption(self, temp_db):
        chart_id = add_chart("https://example.com/chart.png", caption="My chart")
        chart = get_chart(chart_id)
        assert chart["caption"] == "My chart"

    def test_add_chart_empty_url_raises(self, temp_db):
        with pytest.raises(ValueError, match="chart_url is required"):
            add_chart("")

    def test_get_chart_not_found_returns_none(self, temp_db):
        assert get_chart(9999) is None

    def test_get_chart_unattached_by_default(self, temp_db):
        chart_id = add_chart("https://example.com/c.png")
        chart = get_chart(chart_id)
        assert chart["trade_id"] is None
        assert chart["analysis_stage_id"] is None
        assert chart["setup_id"] is None
        assert chart["note_id"] is None


# ---------------------------------------------------------------------------
# update_chart
# ---------------------------------------------------------------------------

class TestUpdateChart:
    def test_update_url_and_caption(self, temp_db):
        chart_id = add_chart("https://old.url/c.png", caption="old")
        update_chart(chart_id, "https://new.url/c.png", "new")
        chart = get_chart(chart_id)
        assert chart["chart_url"] == "https://new.url/c.png"
        assert chart["caption"] == "new"

    def test_update_not_found_raises(self, temp_db):
        with pytest.raises(ValueError, match="not found"):
            update_chart(9999, "https://x.com/c.png")

    def test_update_empty_url_raises(self, temp_db):
        chart_id = add_chart("https://x.com/c.png")
        with pytest.raises(ValueError, match="chart_url is required"):
            update_chart(chart_id, "")


# ---------------------------------------------------------------------------
# delete_chart
# ---------------------------------------------------------------------------

class TestDeleteChart:
    def test_delete_removes_chart(self, temp_db):
        chart_id = add_chart("https://x.com/c.png")
        delete_chart(chart_id)
        assert get_chart(chart_id) is None

    def test_delete_not_found_raises(self, temp_db):
        with pytest.raises(ValueError, match="not found"):
            delete_chart(9999)


# ---------------------------------------------------------------------------
# list_charts
# ---------------------------------------------------------------------------

class TestListCharts:
    def test_list_all(self, temp_db):
        add_chart("https://x.com/1.png")
        add_chart("https://x.com/2.png")
        charts = list_charts()
        assert len(charts) >= 2

    def test_list_unattached(self, temp_db):
        add_chart("https://x.com/u.png")
        charts = list_charts(unattached=True)
        assert all(
            c["trade_id"] is None
            and c["analysis_stage_id"] is None
            and c["setup_id"] is None
            and c["note_id"] is None
            for c in charts
        )

    def test_list_by_trade_id(self, test_user):
        acc_id = _make_account(test_user)
        trade_id = _make_trade(test_user, acc_id)
        chart_id = add_chart("https://x.com/t.png")
        attach_chart("trade", trade_id, chart_id)
        charts = list_charts(trade_id=trade_id)
        assert len(charts) == 1
        assert charts[0]["id"] == chart_id


# ---------------------------------------------------------------------------
# attach_chart / detach_chart
# ---------------------------------------------------------------------------

class TestAttachDetachChart:
    def test_attach_to_trade(self, test_user):
        acc_id = _make_account(test_user)
        trade_id = _make_trade(test_user, acc_id)
        chart_id = add_chart("https://x.com/c.png")
        attach_chart("trade", trade_id, chart_id)
        chart = get_chart(chart_id)
        assert chart["trade_id"] == trade_id

    def test_attach_idempotent_same_entity(self, test_user):
        acc_id = _make_account(test_user)
        trade_id = _make_trade(test_user, acc_id)
        chart_id = add_chart("https://x.com/c.png")
        attach_chart("trade", trade_id, chart_id)
        attach_chart("trade", trade_id, chart_id)  # should not raise
        assert get_chart(chart_id)["trade_id"] == trade_id

    def test_attach_to_different_entity_raises(self, test_user):
        acc_id = _make_account(test_user)
        trade_id1 = _make_trade(test_user, acc_id)
        trade_id2 = _make_trade(test_user, acc_id)
        chart_id = add_chart("https://x.com/c.png")
        attach_chart("trade", trade_id1, chart_id)
        with pytest.raises(ValueError):
            attach_chart("trade", trade_id2, chart_id)

    def test_attach_unknown_entity_type_raises(self, temp_db):
        chart_id = add_chart("https://x.com/c.png")
        with pytest.raises(ValueError, match="Unknown entity type"):
            attach_chart("unknown_type", 1, chart_id)

    def test_attach_chart_not_found_raises(self, temp_db):
        with pytest.raises(ValueError, match="not found"):
            attach_chart("trade", 1, 9999)

    def test_detach_from_trade(self, test_user):
        acc_id = _make_account(test_user)
        trade_id = _make_trade(test_user, acc_id)
        chart_id = add_chart("https://x.com/c.png")
        attach_chart("trade", trade_id, chart_id)
        detach_chart("trade", trade_id, chart_id)
        assert get_chart(chart_id)["trade_id"] is None

    def test_detach_unknown_entity_type_raises(self, temp_db):
        chart_id = add_chart("https://x.com/c.png")
        with pytest.raises(ValueError, match="Unknown entity type"):
            detach_chart("unknown_type", 1, chart_id)

    def test_wrapper_attach_detach_trade(self, test_user):
        acc_id = _make_account(test_user)
        trade_id = _make_trade(test_user, acc_id)
        chart_id = add_chart("https://x.com/c.png")
        attach_chart_to_trade(trade_id, chart_id)
        assert get_chart(chart_id)["trade_id"] == trade_id
        detach_chart_from_trade(trade_id, chart_id)
        assert get_chart(chart_id)["trade_id"] is None
