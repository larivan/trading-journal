
import pytest
from datetime import date, time
from db.notes import (
    create_note,
    get_note,
    update_note,
    delete_note,
    list_notes,
    list_trade_notes,
)
# We need to import the fixture to make it available, 
# even though pytest usually finds it in conftest.py automatically if it's in the same package/root.
# But explicit is better if needed. Assuming conftest.py is in tests/.

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
