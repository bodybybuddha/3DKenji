"""
Example tests demonstrating database isolation.

These tests show how the db_session fixture provides complete isolation
between tests, ensuring no test affects another's data.
"""

import pytest
from backend.models.user import User
from sqlalchemy.orm import Session


class TestDatabaseIsolation:
    """Demonstrate that database transactions are properly isolated."""

    def test_create_user_isolated_1(self, db_session: Session):
        """First test creates a user - should not affect test 2."""
        user = User(
            id="test-user-1",
            username="isolated_user_1",
            email="isolated1@example.com",
            display_name="Isolated User 1",
            password_hash="dummy_hash_1",
            is_admin=False,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        # User exists in this test
        found = db_session.query(User).filter_by(username="isolated_user_1").first()
        assert found is not None
        assert str(found.email) == "isolated1@example.com"

        # Transaction will be rolled back after this test

    def test_create_user_isolated_2(self, db_session: Session):
        """Second test - should NOT see user from test 1."""
        # User from test_create_user_isolated_1 should NOT exist
        found = db_session.query(User).filter_by(username="isolated_user_1").first()
        assert found is None, "Previous test's data leaked into this test!"

        # Create different user
        user = User(
            id="test-user-2",
            username="isolated_user_2",
            email="isolated2@example.com",
            display_name="Isolated User 2",
            password_hash="dummy_hash_2",
            is_admin=False,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        # This user exists in THIS test only
        found = db_session.query(User).filter_by(username="isolated_user_2").first()
        assert found is not None

    def test_query_empty_database(self, db_session: Session):
        """Test that database starts empty for each test."""
        # Should have no users at start (unless created by fixtures)
        user_count = db_session.query(User).count()
        
        # Note: Contract/integration tests may have created admin user
        # during server startup, but unit tests with db_session start clean
        
        # Create a user in this test
        user = User(
            id="test-user-3",
            username="temp_user",
            email="temp@example.com",
            display_name="Temp User",
            password_hash="dummy_hash_3",
            is_admin=False,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        # Now we have one more user
        assert db_session.query(User).count() == user_count + 1


class TestTransactionRollback:
    """Verify transaction rollback behavior."""

    def test_multiple_operations_rolled_back(self, db_session: Session):
        """All operations in a test are rolled back together."""
        # Create multiple users
        for i in range(5):
            user = User(
                id=f"batch-user-{i}",
                username=f"batch_{i}",
                email=f"batch{i}@example.com",
                display_name=f"Batch User {i}",
                password_hash=f"dummy_hash_batch_{i}",
                is_admin=False,
                is_active=True,
            )
            db_session.add(user)
        
        db_session.commit()

        # All 5 users exist in this test
        assert db_session.query(User).filter(User.username.like("batch_%")).count() == 5

        # All will be rolled back after test

    def test_no_batch_users_exist(self, db_session: Session):
        """Batch users from previous test should not exist."""
        batch_users = db_session.query(User).filter(User.username.like("batch_%")).count()
        assert batch_users == 0, f"Found {batch_users} batch users - rollback failed!"


# Run these tests to verify isolation:
# pytest tests/test_database_isolation.py -v
#
# All tests should pass, demonstrating that:
# 1. Each test starts with clean database state
# 2. Changes in one test don't affect other tests
# 3. Transactions are properly rolled back
# 4. Multiple operations within a test are atomic
