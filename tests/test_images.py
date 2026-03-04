# tests/test_images.py — Tests for db/images.py
import pytest

from db.images import (
    add_image,
    get_image,
    update_image,
    delete_image,
    list_images,
    attach_image,
    detach_image,
    attach_image_to_trade,
    detach_image_from_trade,
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
# add_image / get_image
# ---------------------------------------------------------------------------

class TestAddGetImage:
    def test_add_image_returns_id(self, temp_db):
        image_id = add_image("https://example.com/image.png")
        assert isinstance(image_id, int)
        assert image_id > 0

    def test_add_image_with_caption(self, temp_db):
        image_id = add_image("https://example.com/image.png", caption="My image")
        image = get_image(image_id)
        assert image["caption"] == "My image"

    def test_add_image_empty_url_raises(self, temp_db):
        with pytest.raises(ValueError, match="image_url is required"):
            add_image("")

    def test_get_image_not_found_returns_none(self, temp_db):
        assert get_image(9999) is None

    def test_get_image_unattached_by_default(self, temp_db):
        image_id = add_image("https://example.com/i.png")
        image = get_image(image_id)
        assert image["trade_id"] is None
        assert image["analysis_stage_id"] is None
        assert image["setup_id"] is None
        assert image["note_id"] is None


# ---------------------------------------------------------------------------
# update_image
# ---------------------------------------------------------------------------

class TestUpdateImage:
    def test_update_url_and_caption(self, temp_db):
        image_id = add_image("https://old.url/i.png", caption="old")
        update_image(image_id, "https://new.url/i.png", "new")
        image = get_image(image_id)
        assert image["image_url"] == "https://new.url/i.png"
        assert image["caption"] == "new"

    def test_update_not_found_raises(self, temp_db):
        with pytest.raises(ValueError, match="not found"):
            update_image(9999, "https://x.com/i.png")

    def test_update_empty_url_raises(self, temp_db):
        image_id = add_image("https://x.com/i.png")
        with pytest.raises(ValueError, match="image_url is required"):
            update_image(image_id, "")


# ---------------------------------------------------------------------------
# delete_image
# ---------------------------------------------------------------------------

class TestDeleteImage:
    def test_delete_removes_image(self, temp_db):
        image_id = add_image("https://x.com/i.png")
        delete_image(image_id)
        assert get_image(image_id) is None

    def test_delete_not_found_raises(self, temp_db):
        with pytest.raises(ValueError, match="not found"):
            delete_image(9999)


# ---------------------------------------------------------------------------
# list_images
# ---------------------------------------------------------------------------

class TestListImages:
    def test_list_all(self, temp_db):
        add_image("https://x.com/1.png")
        add_image("https://x.com/2.png")
        images = list_images()
        assert len(images) >= 2

    def test_list_unattached(self, temp_db):
        add_image("https://x.com/u.png")
        images = list_images(unattached=True)
        assert all(
            i["trade_id"] is None
            and i["analysis_stage_id"] is None
            and i["setup_id"] is None
            and i["note_id"] is None
            for i in images
        )

    def test_list_by_trade_id(self, test_user):
        acc_id = _make_account(test_user)
        trade_id = _make_trade(test_user, acc_id)
        image_id = add_image("https://x.com/t.png")
        attach_image("trade", trade_id, image_id)
        images = list_images(trade_id=trade_id)
        assert len(images) == 1
        assert images[0]["id"] == image_id


# ---------------------------------------------------------------------------
# attach_image / detach_image
# ---------------------------------------------------------------------------

class TestAttachDetachImage:
    def test_attach_to_trade(self, test_user):
        acc_id = _make_account(test_user)
        trade_id = _make_trade(test_user, acc_id)
        image_id = add_image("https://x.com/i.png")
        attach_image("trade", trade_id, image_id)
        image = get_image(image_id)
        assert image["trade_id"] == trade_id

    def test_attach_idempotent_same_entity(self, test_user):
        acc_id = _make_account(test_user)
        trade_id = _make_trade(test_user, acc_id)
        image_id = add_image("https://x.com/i.png")
        attach_image("trade", trade_id, image_id)
        attach_image("trade", trade_id, image_id)  # should not raise
        assert get_image(image_id)["trade_id"] == trade_id

    def test_attach_to_different_entity_raises(self, test_user):
        acc_id = _make_account(test_user)
        trade_id1 = _make_trade(test_user, acc_id)
        trade_id2 = _make_trade(test_user, acc_id)
        image_id = add_image("https://x.com/i.png")
        attach_image("trade", trade_id1, image_id)
        with pytest.raises(ValueError):
            attach_image("trade", trade_id2, image_id)

    def test_attach_unknown_entity_type_raises(self, temp_db):
        image_id = add_image("https://x.com/i.png")
        with pytest.raises(ValueError, match="Unknown entity type"):
            attach_image("unknown_type", 1, image_id)

    def test_attach_image_not_found_raises(self, temp_db):
        with pytest.raises(ValueError, match="not found"):
            attach_image("trade", 1, 9999)

    def test_detach_from_trade(self, test_user):
        acc_id = _make_account(test_user)
        trade_id = _make_trade(test_user, acc_id)
        image_id = add_image("https://x.com/i.png")
        attach_image("trade", trade_id, image_id)
        detach_image("trade", trade_id, image_id)
        assert get_image(image_id)["trade_id"] is None

    def test_detach_unknown_entity_type_raises(self, temp_db):
        image_id = add_image("https://x.com/i.png")
        with pytest.raises(ValueError, match="Unknown entity type"):
            detach_image("unknown_type", 1, image_id)

    def test_wrapper_attach_detach_trade(self, test_user):
        acc_id = _make_account(test_user)
        trade_id = _make_trade(test_user, acc_id)
        image_id = add_image("https://x.com/i.png")
        attach_image_to_trade(trade_id, image_id)
        assert get_image(image_id)["trade_id"] == trade_id
        detach_image_from_trade(trade_id, image_id)
        assert get_image(image_id)["trade_id"] is None
