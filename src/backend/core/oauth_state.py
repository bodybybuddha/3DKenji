"""Short-lived OAuth PKCE state store (in-process, TTL-based)."""

import time
from typing import Optional

# Module-level state store: {state: {verifier, expires_at, link_user_id?}}
_state_store: dict[str, dict] = {}


def store_state(
    state: str,
    pkce_verifier: str,
    ttl_seconds: int = 300,
    link_user_id: Optional[str] = None,
) -> None:
    """Store OAuth state with PKCE verifier and optional link user ID.

    Args:
        state: OAuth state parameter (random token)
        pkce_verifier: PKCE code verifier
        ttl_seconds: Time-to-live in seconds (default 300 = 5 minutes)
        link_user_id: Optional user ID for linking flow (if present, link to this user)
    """
    expires_at = time.time() + ttl_seconds
    _state_store[state] = {
        "verifier": pkce_verifier,
        "expires_at": expires_at,
        "link_user_id": link_user_id,
    }


def consume_state(state: str) -> tuple[str, Optional[str]]:
    """Pop and return the PKCE verifier and optional link_user_id.

    Args:
        state: OAuth state parameter

    Returns:
        Tuple of (pkce_verifier, link_user_id or None)

    Raises:
        ValueError: If state is invalid or expired
    """
    cleanup_expired_states()

    if state not in _state_store:
        raise ValueError("Invalid or expired state")

    entry = _state_store.pop(state)

    if time.time() > entry["expires_at"]:
        raise ValueError("Invalid or expired state")

    return entry["verifier"], entry.get("link_user_id")


def cleanup_expired_states() -> None:
    """Remove expired state entries."""
    now = time.time()
    expired_keys = [
        key for key, value in _state_store.items() if now > value["expires_at"]
    ]
    for key in expired_keys:
        _state_store.pop(key, None)
