# tests/test_accounts.py — Unit tests for accounts module
import pytest
from db.accounts import (
    create_account,
    list_accounts,
    get_account,
    update_account,
    delete_account,
    set_account_archived,
)


class TestCreateAccount:
    def test_create_account_basic(self, test_user):
        """Test creating a basic account."""
        account_id = create_account(
            test_user,
            name="Test Account",
            broker="Test Broker",
            currency="USD",
            starting_balance=10000.0,
        )
        assert account_id is not None
        assert account_id > 0

    def test_create_account_minimal(self, test_user):
        """Test creating account with minimal fields."""
        account_id = create_account(test_user, name="Minimal", starting_balance=1000.0)
        assert account_id > 0

        account = get_account(account_id, test_user)
        assert account["name"] == "Minimal"
        assert account["broker"] is None

    def test_create_prop_account(self, test_user):
        """Test creating a prop firm account."""
        account_id = create_account(
            test_user,
            name="FTMO",
            broker="FTMO",
            starting_balance=100000.0,
            is_prop=1,
        )
        account = get_account(account_id, test_user)
        assert account["is_prop"] == 1


class TestListAccounts:
    def test_list_empty(self, test_user):
        """Test listing when no accounts exist."""
        accounts = list_accounts(test_user)
        assert accounts == []

    def test_list_accounts(self, test_user):
        """Test listing multiple accounts."""
        create_account(test_user, name="Account 1", starting_balance=1000.0)
        create_account(test_user, name="Account 2", starting_balance=2000.0)

        accounts = list_accounts(test_user)
        assert len(accounts) == 2

    def test_list_excludes_archived(self, test_user):
        """Test that archived accounts are excluded by default."""
        acc1 = create_account(test_user, name="Active", starting_balance=1000.0)
        acc2 = create_account(test_user, name="Archived", starting_balance=2000.0)
        set_account_archived(acc2, test_user, True)

        accounts = list_accounts(test_user, include_archived=False)
        assert len(accounts) == 1
        assert accounts[0]["name"] == "Active"

    def test_list_includes_archived(self, test_user):
        """Test listing with archived accounts included."""
        create_account(test_user, name="Active", starting_balance=1000.0)
        acc2 = create_account(test_user, name="Archived", starting_balance=2000.0)
        set_account_archived(acc2, test_user, True)

        accounts = list_accounts(test_user, include_archived=True)
        assert len(accounts) == 2


class TestGetAccount:
    def test_get_existing(self, test_user):
        """Test getting an existing account."""
        account_id = create_account(
            test_user,
            name="Test",
            broker="Broker",
            currency="EUR",
            starting_balance=5000.0,
        )
        account = get_account(account_id, test_user)

        assert account is not None
        assert account["name"] == "Test"
        assert account["broker"] == "Broker"
        assert account["currency"] == "EUR"
        assert account["starting_balance"] == 5000.0

    def test_get_nonexistent(self, test_user):
        """Test getting a non-existent account."""
        account = get_account(99999, test_user)
        assert account is None


class TestUpdateAccount:
    def test_update_name(self, test_user):
        """Test updating account name."""
        account_id = create_account(test_user, name="Old Name", starting_balance=1000.0)
        update_account(account_id, test_user, {"name": "New Name"})

        account = get_account(account_id, test_user)
        assert account["name"] == "New Name"

    def test_update_multiple_fields(self, test_user):
        """Test updating multiple fields."""
        account_id = create_account(test_user, name="Test", starting_balance=1000.0)
        update_account(account_id, test_user, {
            "name": "Updated",
            "broker": "New Broker",
            "currency": "GBP",
        })

        account = get_account(account_id, test_user)
        assert account["name"] == "Updated"
        assert account["broker"] == "New Broker"
        assert account["currency"] == "GBP"

    def test_update_nonexistent_raises(self, test_user):
        """Test updating non-existent account raises error."""
        with pytest.raises(ValueError, match="not found"):
            update_account(99999, test_user, {"name": "Test"})


class TestDeleteAccount:
    def test_delete_account(self, test_user):
        """Test deleting an account."""
        account_id = create_account(test_user, name="To Delete", starting_balance=1000.0)
        delete_account(account_id, test_user)

        assert get_account(account_id, test_user) is None

    def test_delete_nonexistent_raises(self, test_user):
        """Test deleting non-existent account raises error."""
        with pytest.raises(ValueError, match="not found"):
            delete_account(99999, test_user)


class TestSetAccountArchived:
    def test_archive_account(self, test_user):
        """Test archiving an account."""
        account_id = create_account(test_user, name="Test", starting_balance=1000.0)
        set_account_archived(account_id, test_user, True)

        account = get_account(account_id, test_user)
        assert account["archived"] == 1

    def test_unarchive_account(self, test_user):
        """Test unarchiving an account."""
        account_id = create_account(test_user, name="Test", starting_balance=1000.0)
        set_account_archived(account_id, test_user, True)
        set_account_archived(account_id, test_user, False)

        account = get_account(account_id, test_user)
        assert account["archived"] == 0
