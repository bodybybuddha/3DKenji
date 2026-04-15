"""OAuth/OIDC service for authentication flows."""

import base64
import hashlib
import secrets
import time
import uuid
from typing import Optional
from urllib.parse import urlencode

import httpx
from authlib.jose import JsonWebToken, JsonWebKey
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.models.user import User
from backend.models.oauth_identity import OAuthIdentity

# Discovery config cache: {issuer_url: (config_dict, expiry_timestamp)}
_discovery_cache: dict[str, tuple[dict, float]] = {}

# JWKS cache: {jwks_uri: (keyset, expiry_timestamp)}
_jwks_cache: dict[str, tuple[object, float]] = {}


def get_oidc_discovery_config(issuer_url: str) -> dict:
    """Fetch OIDC discovery configuration from issuer.

    Caches the result for 1 hour.

    Args:
        issuer_url: OIDC issuer URL (e.g. https://auth.example.com/application/o/app/)

    Returns:
        Discovery configuration dict

    Raises:
        RuntimeError: On fetch failure
    """
    now = time.time()

    # Check cache
    if issuer_url in _discovery_cache:
        config, expiry = _discovery_cache[issuer_url]
        if now < expiry:
            return config

    # Fetch from well-known endpoint
    discovery_url = issuer_url.rstrip("/") + "/.well-known/openid-configuration"

    try:
        response = httpx.get(discovery_url, timeout=10.0)
        response.raise_for_status()
        config = response.json()
    except Exception as e:
        raise RuntimeError(f"Failed to fetch OIDC discovery config: {e}")

    # Cache for 1 hour
    _discovery_cache[issuer_url] = (config, now + 3600)

    return config


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code verifier and challenge pair.

    Returns:
        Tuple of (code_verifier, code_challenge) using S256 method
    """
    # Generate code_verifier: 43-128 chars from [A-Za-z0-9_.-~]
    code_verifier = secrets.token_urlsafe(96)  # ~128 chars

    # Generate code_challenge: base64url(SHA256(code_verifier))
    challenge_bytes = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode().rstrip("=")

    return code_verifier, code_challenge


def build_authorization_url(
    discover_config: dict,
    state: str,
    code_challenge: str,
    client_id: str,
    callback_url: str,
    scopes: str,
) -> str:
    """Build OAuth authorization URL.

    Args:
        discover_config: OIDC discovery configuration
        state: OAuth state parameter
        code_challenge: PKCE code challenge
        client_id: OAuth client ID
        callback_url: OAuth callback URL
        scopes: Space-separated scopes

    Returns:
        Authorization URL
    """
    auth_endpoint = discover_config["authorization_endpoint"]

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": callback_url,
        "scope": scopes,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    return f"{auth_endpoint}?{urlencode(params)}"


def exchange_code_for_tokens(
    discover_config: dict,
    code: str,
    code_verifier: str,
    client_id: str,
    client_secret: str,
    callback_url: str,
) -> dict:
    """Exchange authorization code for tokens.

    Args:
        discover_config: OIDC discovery configuration
        code: Authorization code
        code_verifier: PKCE code verifier
        client_id: OAuth client ID
        client_secret: OAuth client secret (never logged)
        callback_url: OAuth callback URL

    Returns:
        Token response dict

    Raises:
        RuntimeError: On token exchange failure
    """
    token_endpoint = discover_config["token_endpoint"]

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": callback_url,
        "client_id": client_id,
        "client_secret": client_secret,
        "code_verifier": code_verifier,
    }

    try:
        response = httpx.post(token_endpoint, data=payload, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise RuntimeError(f"Token exchange failed: {e}")


def extract_id_token_claims(
    id_token: str,
    client_id: str,
    issuer_url: str,
    jwks_uri: str,
) -> dict:
    """Validate and decode ID token JWT.

    Args:
        id_token: ID token JWT string
        client_id: OAuth client ID (for aud verification)
        issuer_url: OIDC issuer URL (for iss verification)
        jwks_uri: JWKS endpoint URL

    Returns:
        Decoded claims dict

    Raises:
        ValueError: If ID token validation fails
    """
    # Fetch JWKS (with caching)
    keyset = _fetch_jwks(jwks_uri)

    # Decode and validate
    jwt = JsonWebToken(["RS256", "HS256"])

    try:
        claims = jwt.decode(
            id_token,
            keyset,
            claims_options={
                "iss": {"essential": True, "value": issuer_url},
                "aud": {"essential": True, "value": client_id},
                "exp": {"essential": True},
            },
        )
        claims.validate()
        return dict(claims)
    except Exception:
        raise ValueError("Invalid ID token")


def _fetch_jwks(jwks_uri: str) -> object:
    """Fetch JWKS from endpoint with 1-hour cache.

    Args:
        jwks_uri: JWKS endpoint URL

    Returns:
        JsonWebKey keyset
    """
    now = time.time()

    # Check cache
    if jwks_uri in _jwks_cache:
        keyset, expiry = _jwks_cache[jwks_uri]
        if now < expiry:
            return keyset

    # Fetch JWKS
    try:
        response = httpx.get(jwks_uri, timeout=10.0)
        response.raise_for_status()
        jwks_data = response.json()
    except Exception as e:
        raise RuntimeError(f"Failed to fetch JWKS: {e}")

    # Import keyset
    keyset = JsonWebKey.import_key_set(jwks_data)

    # Cache for 1 hour
    _jwks_cache[jwks_uri] = (keyset, now + 3600)

    return keyset


def find_or_create_user_from_claims(
    db: Session,
    provider: str,
    claims: dict,
) -> tuple[User, bool]:
    """Find existing user or create new user from OIDC claims.

    Args:
        db: Database session
        provider: OAuth provider name
        claims: ID token claims

    Returns:
        Tuple of (User, is_new_user)

    Raises:
        ValueError: If required claims are missing
    """
    # Extract required and optional claims
    sub = claims.get("sub")
    if not sub:
        raise ValueError("Missing required claim: sub")

    email = claims.get("email")
    name = claims.get("name") or claims.get("preferred_username")
    preferred_username = claims.get("preferred_username")

    # Look up existing OAuthIdentity by (provider, sub)
    existing_identity = db.execute(
        select(OAuthIdentity).where(
            OAuthIdentity.provider == provider,
            OAuthIdentity.provider_user_id == sub,
        )
    ).scalar_one_or_none()

    if existing_identity:
        # User already linked
        user = db.execute(
            select(User).where(User.id == existing_identity.user_id)
        ).scalar_one()

        # Update identity metadata
        existing_identity.provider_email = email  # type: ignore
        existing_identity.provider_display_name = name  # type: ignore
        db.commit()

        return user, False

    # Not found by sub; try matching by email if provided
    if email:
        user_by_email = db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()

        if user_by_email:
            # Auto-link to existing user
            _create_oauth_identity(db, user_by_email.id, provider, sub, email, name)  # type: ignore
            db.commit()
            return user_by_email, False

    # No match found; create new user
    # Generate unique username
    base_username = preferred_username or sub[:20]
    username = _make_unique_username(db, base_username)

    # Generate email if not provided
    user_email = email or f"{sub}@{provider}.oidc"

    # Generate display_name
    display_name = name or username

    # Create user with no password (OIDC-only)
    user = User(
        id=str(uuid.uuid4()),
        username=username,
        nickname=username,  # Will be made unique by UserService if needed
        email=user_email,
        display_name=display_name,
        password_hash=None,
        is_admin=False,
        is_active=True,
    )

    db.add(user)
    db.flush()  # Get user.id

    # Create OAuth identity
    _create_oauth_identity(db, user.id, provider, sub, email, name)  # type: ignore

    db.commit()
    db.refresh(user)

    return user, True


def _create_oauth_identity(
    db: Session,
    user_id: str,
    provider: str,
    provider_user_id: str,
    provider_email: Optional[str],
    provider_display_name: Optional[str],
) -> OAuthIdentity:
    """Create new OAuth identity record."""
    identity = OAuthIdentity(
        id=str(uuid.uuid4()),
        user_id=user_id,
        provider=provider,
        provider_user_id=provider_user_id,
        provider_email=provider_email,
        provider_display_name=provider_display_name,
    )
    db.add(identity)
    return identity


def _make_unique_username(db: Session, base: str) -> str:
    """Generate a unique username by appending _N suffix if needed."""
    # Sanitize base
    base = base.lower()[:50]  # Limit length

    candidate = base
    counter = 1

    while db.execute(select(User).where(User.username == candidate)).scalar_one_or_none():
        counter += 1
        candidate = f"{base}_{counter}"

    return candidate
