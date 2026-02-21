
import pytest
from datetime import date, time
from db.notes import (
    attach_note_to_analysis_stage,
    attach_note_to_trade,
    count_notes_by_trade,
    create_note,
    detach_note_from_analysis_stage,
    detach_note_from_trade,
    get_note,
    list_analysis_stage_notes,
    list_notes,
    list_trade_notes,
    update_note,
    delete_note,
)
from db.accounts import create_account
from db.setups import create_setup
from db.analysis import add_analysis, add_analysis_stage
from db.trades import create_trade


@pytest.fixture
def note_m2m_deps(temp_db):
    """Dependencies for M2M note tests: a trade and an analysis stage."""
    account_id = create_account(name="Acc", starting_balance=10000.0)
    setup_id = create_setup(name="S")
    analysis_id = add_analysis({"date_local": "2026-01-01"})
    stage_id = add_analysis_stage({
        "analysis_id": analysis_id,
        "type": "pre-market",
        "time_local": "08:00:00",
    })
    trade_id = create_trade({
        "local_tz": "UTC+3",
        "date_local": "2026-01-01",
        "time_local": "09:00:00",
        "account_id": account_id,
        "setup_id": setup_id,
        "asset": "EUR/USD",
        "session": "LOKZ",
        "state": "Open",
        "is_missed": 0,
    })
    return {"trade_id": trade_id, "stage_id": stage_id}


def test_create_note(temp_db):
    note_id = create_note({"body": "Test Note"})
    assert note_id is not None
    
    note = get_note(note_id)
    assert note["body"] == "Test Note"
    assert note["date_local"] == date.today().isoformat()

def test_create_note_with_date(temp_db):
    note_id = create_note({"body": "Old Note", "date_local": "2023-01-01"})
    note = get_note(note_id)
    assert note["date_local"] == "2023-01-01"

def test_create_note_validation(temp_db):
    with pytest.raises(ValueError, match="body is required for note"):
        create_note({"body": ""})
    with pytest.raises(ValueError, match="body is required for note"):
        create_note({})

def test_update_note(temp_db):
    note_id = create_note({"body": "Original"})
    update_note(note_id, {"body": "Updated"})
    note = get_note(note_id)
    assert note["body"] == "Updated"

def test_update_note_not_found(temp_db):
    with pytest.raises(ValueError, match="Note #999 not found"):
        update_note(999, {"body": "New"})

def test_delete_note(temp_db):
    note_id = create_note({"body": "To Delete"})
    delete_note(note_id)
    assert get_note(note_id) is None
    
    with pytest.raises(ValueError, match="Note #999 not found"):
        delete_note(999)

def test_list_notes(temp_db):
    create_note({"body": "Note 1"})
    create_note({"body": "Note 2"})
    notes = list_notes()
    assert len(notes) == 2
    assert any(n["body"] == "Note 1" for n in notes)
    assert any(n["body"] == "Note 2" for n in notes)


def test_list_notes_filter_query(temp_db):
    create_note({"body": "EUR/USD observation"})
    create_note({"body": "GBP/USD note"})
    results = list_notes({"query": "EUR"})
    assert len(results) == 1
    assert results[0]["body"] == "EUR/USD observation"


def test_list_notes_filter_date_range(temp_db):
    create_note({"body": "Early", "date_local": "2026-01-01"})
    create_note({"body": "Mid", "date_local": "2026-01-15"})
    create_note({"body": "Late", "date_local": "2026-02-01"})
    results = list_notes({"date_from": "2026-01-10", "date_to": "2026-01-20"})
    assert len(results) == 1
    assert results[0]["body"] == "Mid"


def test_list_notes_order_by_invalid(temp_db):
    with pytest.raises(ValueError):
        list_notes(order_by="nonexistent")


class TestGetNote:
    def test_get_existing(self, temp_db):
        note_id = create_note({"body": "Hello"})
        note = get_note(note_id)
        assert note is not None
        assert note["body"] == "Hello"

    def test_get_nonexistent(self, temp_db):
        assert get_note(99999) is None


class TestTradeNotes:
    def test_attach_note_to_trade(self, note_m2m_deps):
        trade_id = note_m2m_deps["trade_id"]
        note_id = create_note({"body": "Trade note"})
        attach_note_to_trade(trade_id, note_id)
        notes = list_trade_notes(trade_id)
        assert len(notes) == 1
        assert notes[0]["body"] == "Trade note"

    def test_attach_note_idempotent(self, note_m2m_deps):
        """INSERT OR IGNORE — повторное прикрепление не дублирует запись."""
        trade_id = note_m2m_deps["trade_id"]
        note_id = create_note({"body": "Dup"})
        attach_note_to_trade(trade_id, note_id)
        attach_note_to_trade(trade_id, note_id)
        assert len(list_trade_notes(trade_id)) == 1

    def test_detach_note_from_trade(self, note_m2m_deps):
        trade_id = note_m2m_deps["trade_id"]
        note_id = create_note({"body": "To detach"})
        attach_note_to_trade(trade_id, note_id)
        detach_note_from_trade(trade_id, note_id)
        assert list_trade_notes(trade_id) == []

    def test_detach_nonexistent_link_silent(self, note_m2m_deps):
        """Отвязка несуществующей связи не бросает исключение."""
        trade_id = note_m2m_deps["trade_id"]
        detach_note_from_trade(trade_id, 99999)  # should not raise

    def test_list_trade_notes_empty(self, note_m2m_deps):
        assert list_trade_notes(note_m2m_deps["trade_id"]) == []

    def test_list_trade_notes_none_trade_id(self, temp_db):
        assert list_trade_notes(None) == []

    def test_attach_none_args_silent(self, temp_db):
        attach_note_to_trade(None, 1)  # should not raise
        attach_note_to_trade(1, None)  # should not raise

    def test_count_notes_by_trade(self, note_m2m_deps):
        trade_id = note_m2m_deps["trade_id"]
        n1 = create_note({"body": "A"})
        n2 = create_note({"body": "B"})
        attach_note_to_trade(trade_id, n1)
        attach_note_to_trade(trade_id, n2)
        counts = count_notes_by_trade()
        assert counts[n1] == 1
        assert counts[n2] == 1

    def test_delete_note_detaches_from_trade(self, note_m2m_deps):
        """Удаление заметки каскадно убирает связь с трейдом."""
        trade_id = note_m2m_deps["trade_id"]
        note_id = create_note({"body": "Cascade"})
        attach_note_to_trade(trade_id, note_id)
        delete_note(note_id)
        assert list_trade_notes(trade_id) == []


class TestAnalysisStageNotes:
    def test_attach_note_to_stage(self, note_m2m_deps):
        stage_id = note_m2m_deps["stage_id"]
        note_id = create_note({"body": "Stage note"})
        attach_note_to_analysis_stage(stage_id, note_id)
        notes = list_analysis_stage_notes(stage_id)
        assert len(notes) == 1
        assert notes[0]["body"] == "Stage note"

    def test_attach_note_to_stage_idempotent(self, note_m2m_deps):
        stage_id = note_m2m_deps["stage_id"]
        note_id = create_note({"body": "Dup"})
        attach_note_to_analysis_stage(stage_id, note_id)
        attach_note_to_analysis_stage(stage_id, note_id)
        assert len(list_analysis_stage_notes(stage_id)) == 1

    def test_detach_note_from_stage(self, note_m2m_deps):
        stage_id = note_m2m_deps["stage_id"]
        note_id = create_note({"body": "Detach"})
        attach_note_to_analysis_stage(stage_id, note_id)
        detach_note_from_analysis_stage(stage_id, note_id)
        assert list_analysis_stage_notes(stage_id) == []

    def test_detach_nonexistent_link_silent(self, note_m2m_deps):
        stage_id = note_m2m_deps["stage_id"]
        detach_note_from_analysis_stage(stage_id, 99999)  # should not raise

    def test_list_stage_notes_empty(self, note_m2m_deps):
        assert list_analysis_stage_notes(note_m2m_deps["stage_id"]) == []

    def test_list_stage_notes_none_stage_id(self, temp_db):
        assert list_analysis_stage_notes(None) == []

    def test_attach_none_args_silent(self, temp_db):
        attach_note_to_analysis_stage(None, 1)  # should not raise
        attach_note_to_analysis_stage(1, None)  # should not raise

    def test_delete_note_detaches_from_stage(self, note_m2m_deps):
        """Удаление заметки каскадно убирает связь со стадией анализа."""
        stage_id = note_m2m_deps["stage_id"]
        note_id = create_note({"body": "Cascade"})
        attach_note_to_analysis_stage(stage_id, note_id)
        delete_note(note_id)
        assert list_analysis_stage_notes(stage_id) == []
