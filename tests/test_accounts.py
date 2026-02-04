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
    def test_create_account_basic(self, temp_db):
        """Test creating a basic account."""
        account_id = create_account(
            name="Test Account",
            broker="Test Broker",
            currency="USD",
            starting_balance=10000.0,
        )
        assert account_id is not None
        assert account_id > 0

    def test_create_account_minimal(self, temp_db):
        """Test creating account with minimal fields."""
        account_id = create_account(name="Minimal", starting_balance=1000.0)
        assert account_id > 0
        
        account = get_account(account_id)
        assert account["name"] == "Minimal"
        assert account["broker"] is None

    def test_create_prop_account(self, temp_db):
        """Test creating a prop firm account."""
        account_id = create_account(
            name="FTMO",
            broker="FTMO",
            starting_balance=100000.0,
            is_prop=1,
        )
        account = get_account(account_id)
        assert account["is_prop"] == 1


class TestListAccounts:
    def test_list_empty(self, temp_db):
        """Test listing when no accounts exist."""
        accounts = list_accounts()
        assert accounts == []

    def test_list_accounts(self, temp_db):
        """Test listing multiple accounts."""
        create_account(name="Account 1", starting_balance=1000.0)
        create_account(name="Account 2", starting_balance=2000.0)
        
        accounts = list_accounts()
        assert len(accounts) == 2

    def test_list_excludes_archived(self, temp_db):
        """Test that archived accounts are excluded by default."""
        acc1 = create_account(name="Active", starting_balance=1000.0)
        acc2 = create_account(name="Archived", starting_balance=2000.0)
        set_account_archived(acc2, True)
        
        accounts = list_accounts(include_archived=False)
        assert len(accounts) == 1
        assert accounts[0]["name"] == "Active"

    def test_list_includes_archived(self, temp_db):
        """Test listing with archived accounts included."""
        create_account(name="Active", starting_balance=1000.0)
        acc2 = create_account(name="Archived", starting_balance=2000.0)
        set_account_archived(acc2, True)
        
        accounts = list_accounts(include_archived=True)
        assert len(accounts) == 2


class TestGetAccount:
    def test_get_existing(self, temp_db):
        """Test getting an existing account."""
        account_id = create_account(
            name="Test",
            broker="Broker",
            currency="EUR",
            starting_balance=5000.0,
        )
        account = get_account(account_id)
        
        assert account is not None
        assert account["name"] == "Test"
        assert account["broker"] == "Broker"
        assert account["currency"] == "EUR"
        assert account["starting_balance"] == 5000.0

    def test_get_nonexistent(self, temp_db):
        """Test getting a non-existent account."""
        account = get_account(99999)
        assert account is None


class TestUpdateAccount:
    def test_update_name(self, temp_db):
        """Test updating account name."""
        account_id = create_account(name="Old Name", starting_balance=1000.0)
        update_account(account_id, {"name": "New Name"})
        
        account = get_account(account_id)
        assert account["name"] == "New Name"

    def test_update_multiple_fields(self, temp_db):
        """Test updating multiple fields."""
        account_id = create_account(name="Test", starting_balance=1000.0)
        update_account(account_id, {
            "name": "Updated",
            "broker": "New Broker",
            "currency": "GBP",
        })
        
        account = get_account(account_id)
        assert account["name"] == "Updated"
        assert account["broker"] == "New Broker"
        assert account["currency"] == "GBP"

    def test_update_nonexistent_raises(self, temp_db):
        """Test updating non-existent account raises error."""
        with pytest.raises(ValueError, match="not found"):
            update_account(99999, {"name": "Test"})


class TestDeleteAccount:
    def test_delete_account(self, temp_db):
        """Test deleting an account."""
        account_id = create_account(name="To Delete", starting_balance=1000.0)
        delete_account(account_id)
        
        assert get_account(account_id) is None

    def test_delete_nonexistent_raises(self, temp_db):
        """Test deleting non-existent account raises error."""
        with pytest.raises(ValueError, match="not found"):
            delete_account(99999)


class TestSetAccountArchived:
    def test_archive_account(self, temp_db):
        """Test archiving an account."""
        account_id = create_account(name="Test", starting_balance=1000.0)
        set_account_archived(account_id, True)
        
        account = get_account(account_id)
        assert account["archived"] == 1

    def test_unarchive_account(self, temp_db):
        """Test unarchiving an account."""
        account_id = create_account(name="Test", starting_balance=1000.0)
        set_account_archived(account_id, True)
        set_account_archived(account_id, False)
        
        account = get_account(account_id)
        assert account["archived"] == 0
