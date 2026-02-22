import pytest
from db.setups import (
    create_setup,
    get_setup,
    update_setup,
    delete_setup,
    list_setups,
)


def test_create_setup(test_user):
    setup_id = create_setup(test_user, "Trend Following", "Follow the trend")
    assert setup_id is not None

    setup = get_setup(setup_id, test_user)
    assert setup["name"] == "Trend Following"
    assert setup["description"] == "Follow the trend"


def test_create_setup_validation(test_user):
    with pytest.raises(ValueError, match="name is required"):
        create_setup(test_user, "")
    with pytest.raises(ValueError, match="name is required"):
        create_setup(test_user, None)


def test_update_setup(test_user):
    setup_id = create_setup(test_user, "Original")
    update_setup(setup_id, test_user, {"name": "Updated", "description": "New Desc"})

    setup = get_setup(setup_id, test_user)
    assert setup["name"] == "Updated"
    assert setup["description"] == "New Desc"


def test_update_setup_not_found(test_user):
    with pytest.raises(ValueError, match="Setup #999 not found"):
        update_setup(999, test_user, {"name": "New"})


def test_delete_setup(test_user):
    setup_id = create_setup(test_user, "To Delete")
    delete_setup(setup_id, test_user)
    assert get_setup(setup_id, test_user) is None

    with pytest.raises(ValueError, match="Setup #999 not found"):
        delete_setup(999, test_user)


def test_list_setups(test_user):
    create_setup(test_user, "Setup A")
    create_setup(test_user, "Setup B")
    setups = list_setups(test_user)
    assert len(setups) == 2
    assert setups[0]["name"] == "Setup A"
    assert setups[1]["name"] == "Setup B"


def test_list_setups_filter(test_user):
    create_setup(test_user, "Alpha")
    create_setup(test_user, "Beta")
    results = list_setups(test_user, filters={"query": "alp"})
    assert len(results) == 1
    assert results[0]["name"] == "Alpha"
