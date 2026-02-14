
import pytest
from db.charts import (
    add_chart,
    get_chart,
    update_chart,
    delete_chart,
    list_charts,
    attach_chart_to_trade,
    attach_chart_to_note,
)
from db.trades import create_trade
from db.notes import create_note
from db.accounts import create_account
from db.setups import create_setup
from db.analysis import add_analysis, ANALYSIS_STATE_VALUES

def test_add_chart(temp_db):
    chart_id = add_chart("http://example.com/image.png", "Caption")
    assert chart_id is not None
    
    chart = get_chart(chart_id)
    assert chart["chart_url"] == "http://example.com/image.png"
    assert chart["caption"] == "Caption"

def test_add_chart_validation(temp_db):
    with pytest.raises(ValueError, match="chart_url is required"):
        add_chart("")

def test_update_chart(temp_db):
    chart_id = add_chart("original.png")
    update_chart(chart_id, "updated.png", "New Caption")
    
    chart = get_chart(chart_id)
    assert chart["chart_url"] == "updated.png"
    assert chart["caption"] == "New Caption"

def test_delete_chart(temp_db):
    chart_id = add_chart("delete.png")
    delete_chart(chart_id)
    assert get_chart(chart_id) is None

def test_list_charts(temp_db):
    add_chart("c1.png")
    add_chart("c2.png")
    charts = list_charts()
    assert len(charts) == 2

def test_attach_chart_to_trade(temp_db):
    # Setup dependencies for trade
    acc_id = create_account(name="Acc", starting_balance=1000.0)
    setup_id = create_setup(name="Setup")
    anal_id = add_analysis({"date_local": "2023-01-01"})
    
    trade_id = create_trade({
        "account_id": acc_id,
        "setup_id": setup_id,
        "analysis_id": anal_id,
        "asset": "EURUSD",
        "date_local": "2023-01-01",
        "time_local": "12:00:00",
        "local_tz": "UTC+3",
        "session": "NYKZ",
        "state": "Open",
    })
    
    chart_id = add_chart("trade_chart.png")
    attach_chart_to_trade(trade_id, chart_id)
    
    chart = get_chart(chart_id)
    assert chart["trade_id"] == trade_id

def test_attach_chart_to_note(temp_db):
    note_id = create_note({"body": "My Note"})
    chart_id = add_chart("note_chart.png")
    attach_chart_to_note(note_id, chart_id)
    
    chart = get_chart(chart_id)
    assert chart["note_id"] == note_id

def test_attach_constraint(temp_db):
    # Cannot attach to trade AND note
    acc_id = create_account(name="Acc", starting_balance=1000.0)
    setup_id = create_setup(name="Setup")
    anal_id = add_analysis({"date_local": "2023-01-01"})

    trade_id = create_trade({
         "account_id": acc_id,
         "setup_id": setup_id,
         "analysis_id": anal_id,
         "date_local": "2023-01-01",
         "time_local": "12:00:00",
         "asset": "EURUSD",
         "local_tz": "UTC+3",
         "session": "NYKZ",
         "state": "Open",
    })
    note_id = create_note({"body": "My Note"})
    
    chart_id = add_chart("conflict.png")
    
    attach_chart_to_trade(trade_id, chart_id)
    
    # Should fail when attaching to note
    with pytest.raises(ValueError, match="Chart is already attached to another entity"):
        attach_chart_to_note(note_id, chart_id)

def test_detach_chart(temp_db):
    note_id = create_note({"body": "Note to detach"})
    chart_id = add_chart("detach.png")
    
    attach_chart_to_note(note_id, chart_id)
    chart = get_chart(chart_id)
    assert chart["note_id"] == note_id
    
    from db.charts import detach_chart_from_note
    detach_chart_from_note(note_id, chart_id)
    
    chart = get_chart(chart_id)
    assert chart["note_id"] is None

def test_db_check_constraint(db_conn):
    # Create dependencies so FKs don't fail first
    # We need to use valid IDs.
    # Note: helpers like create_note commit by default if no conn passed, 
    # but here we want to use the same db_conn.
    # Actually, create_note logic: conn, own = _managed_conn(conn).
    # If we pass db_conn, it uses it and doesn't close.
    # But helpers normalize data etc.
    # Let's just use SQL to create dummies to be purely low-level or use helpers.
    # Helpers are better.
    
    # We need to import helpers inside or top level.
    # They are imported at top.
    
    # Create Note
    # create_note(data, conn=db_conn) - db/notes.py signature?
    # db/notes.py: def create_note(data, *, conn=None) -> int
    note_id = create_note({"body": "Dummy"}, conn=db_conn)
    
    # Create Trade
    # We need all fields...
    acc_id = create_account(name="Acc2", starting_balance=100.0, conn=db_conn)
    setup_id = create_setup(name="S2", conn=db_conn)
    anal_id = add_analysis({"date_local": "2023-01-01"}, conn=db_conn)
    
    trade_id = create_trade({
        "account_id": acc_id,
        "setup_id": setup_id,
        "analysis_id": anal_id,
        "asset": "EURUSD",
        "date_local": "2023-01-01",
        "time_local": "12:00:00",
        "local_tz": "UTC+3",
        "session": "NYKZ",
        "state": "Open",
    }, conn=db_conn)

    # Verify that SQLite enforces the CHECK constraint
    # Insert a chart with TWO foreign keys set to valid IDs
    with pytest.raises(Exception, match="CHECK constraint failed"):
        db_conn.execute(
            "INSERT INTO charts (chart_url, trade_id, note_id) VALUES (?, ?, ?)",
            ("violation.png", trade_id, note_id)
        )

def test_attach_nonexistent_chart(temp_db):
     # NOTE: The implementation raises "Chart #{id} not found."
     with pytest.raises(ValueError, match="Chart #999 not found"):
         attach_chart_to_trade(1, 999)
