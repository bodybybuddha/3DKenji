import pytest

from backend.core import oauth_state


@pytest.fixture(autouse=True)
def clear_oauth_state_store():
    oauth_state._state_store.clear()
    yield
    oauth_state._state_store.clear()


def test_store_and_consume_state_happy_path():
    oauth_state.store_state("state-1", "verifier-1")

    verifier, link_user_id = oauth_state.consume_state("state-1")

    assert verifier == "verifier-1"
    assert link_user_id is None


def test_store_and_consume_state_with_link_user_id():
    oauth_state.store_state("state-2", "verifier-2", link_user_id="user-123")

    verifier, link_user_id = oauth_state.consume_state("state-2")

    assert verifier == "verifier-2"
    assert link_user_id == "user-123"


def test_consume_state_unknown_raises_value_error():
    with pytest.raises(ValueError, match="Invalid or expired state"):
        oauth_state.consume_state("missing-state")


def test_consume_state_expired_raises_value_error():
    oauth_state.store_state("expired-state", "verifier-expired", ttl_seconds=0)

    with pytest.raises(ValueError, match="Invalid or expired state"):
        oauth_state.consume_state("expired-state")


def test_state_is_single_use():
    oauth_state.store_state("state-3", "verifier-3")

    first_verifier, first_link_user_id = oauth_state.consume_state("state-3")

    assert first_verifier == "verifier-3"
    assert first_link_user_id is None

    with pytest.raises(ValueError, match="Invalid or expired state"):
        oauth_state.consume_state("state-3")


def test_cleanup_expired_states_removes_expired_entries_without_error():
    oauth_state.store_state("expired-state", "verifier-expired", ttl_seconds=0)
    oauth_state.store_state("active-state", "verifier-active", ttl_seconds=300)

    oauth_state.cleanup_expired_states()

    assert "expired-state" not in oauth_state._state_store
    assert "active-state" in oauth_state._state_store