
import pytest
from db.setups import (
    create_setup,
    get_setup,
    update_setup,
    delete_setup,
    list_setups,
)

def test_create_setup(temp_db):
    setup_id = create_setup("Trend Following", "Follow the trend")
    assert setup_id is not None
    
    setup = get_setup(setup_id)
    assert setup["name"] == "Trend Following"
    assert setup["description"] == "Follow the trend"

def test_create_setup_validation(temp_db):
    with pytest.raises(ValueError, match="name is required"):
        create_setup("")
    with pytest.raises(ValueError, match="name is required"):
        create_setup(None)

def test_update_setup(temp_db):
    setup_id = create_setup("Original")
    update_setup(setup_id, {"name": "Updated", "description": "New Desc"})
    
    setup = get_setup(setup_id)
    assert setup["name"] == "Updated"
    assert setup["description"] == "New Desc"

def test_update_setup_not_found(temp_db):
    with pytest.raises(ValueError, match="Setup #999 not found"):
        update_setup(999, {"name": "New"})

def test_delete_setup(temp_db):
    setup_id = create_setup("To Delete")
    delete_setup(setup_id)
    assert get_setup(setup_id) is None
    
    with pytest.raises(ValueError, match="Setup #999 not found"):
        delete_setup(999)

def test_list_setups(temp_db):
    create_setup("Setup A")
    create_setup("Setup B")
    setups = list_setups()
    assert len(setups) == 2
    assert setups[0]["name"] == "Setup A"
    assert setups[1]["name"] == "Setup B"

def test_list_setups_filter(temp_db):
    create_setup("Alpha")
    create_setup("Beta")
    results = list_setups(filters={"query": "alp"})
    assert len(results) == 1
    assert results[0]["name"] == "Alpha"
