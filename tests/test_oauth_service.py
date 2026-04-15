import base64
import hashlib
import re
from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import select

from backend.models.oauth_identity import OAuthIdentity
from backend.services import oauth_service
from backend.services.user_service import UserService


@pytest.fixture(autouse=True)
def clear_oauth_service_caches():
    oauth_service._discovery_cache.clear()
    oauth_service._jwks_cache.clear()
    yield
    oauth_service._discovery_cache.clear()
    oauth_service._jwks_cache.clear()


def test_generate_pkce_pair_returns_valid_verifier_and_challenge():
    verifier, challenge = oauth_service.generate_pkce_pair()

    expected_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).decode().rstrip("=")

    assert 43 <= len(verifier) <= 130
    assert challenge == expected_challenge
    assert "=" not in challenge
    assert re.fullmatch(r"[A-Za-z0-9_-]+", challenge)


def test_get_oidc_discovery_config_uses_cache_until_ttl_expires(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"issuer": "https://issuer.example"}

    calls = []
    current_time = [1000.0]

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return FakeResponse()

    monkeypatch.setattr(oauth_service.httpx, "get", fake_get)
    monkeypatch.setattr(oauth_service.time, "time", lambda: current_time[0])

    first = oauth_service.get_oidc_discovery_config("https://issuer.example")
    second = oauth_service.get_oidc_discovery_config("https://issuer.example")
    current_time[0] += 3601
    third = oauth_service.get_oidc_discovery_config("https://issuer.example")

    assert first == {"issuer": "https://issuer.example"}
    assert second == first
    assert third == first
    assert len(calls) == 2
    assert calls[0][0] == "https://issuer.example/.well-known/openid-configuration"


def test_get_oidc_discovery_config_raises_runtime_error_on_http_failure(monkeypatch):
    def fake_get(url, timeout):
        raise RuntimeError("network down")

    monkeypatch.setattr(oauth_service.httpx, "get", fake_get)

    with pytest.raises(RuntimeError, match="Failed to fetch OIDC discovery config"):
        oauth_service.get_oidc_discovery_config("https://issuer.example")


def test_build_authorization_url_contains_expected_parameters():
    url = oauth_service.build_authorization_url(
        discover_config={"authorization_endpoint": "https://issuer.example/authorize"},
        state="oauth-state",
        code_challenge="challenge-value",
        client_id="client-id",
        callback_url="https://app.example/callback",
        scopes="openid email profile",
    )

    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "issuer.example"
    assert parsed.path == "/authorize"
    assert query["response_type"] == ["code"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"] == ["challenge-value"]
    assert query["state"] == ["oauth-state"]
    assert query["client_id"] == ["client-id"]
    assert query["redirect_uri"] == ["https://app.example/callback"]


def test_extract_id_token_claims_decodes_and_returns_claims(monkeypatch):
    class FakeClaims(dict):
        def validate(self):
            self["validated"] = True

    class FakeJWT:
        def __init__(self):
            self.called_with = None

        def decode(self, id_token, keyset, claims_options):
            self.called_with = (id_token, keyset, claims_options)
            return FakeClaims(sub="sub-123", email="user@example.com")

    fake_jwt = FakeJWT()

    monkeypatch.setattr(oauth_service, "_fetch_jwks", lambda jwks_uri: "fake-keyset")
    monkeypatch.setattr(oauth_service, "JsonWebToken", lambda algorithms: fake_jwt)

    claims = oauth_service.extract_id_token_claims(
        id_token="id-token",
        client_id="client-id",
        issuer_url="https://issuer.example",
        jwks_uri="https://issuer.example/jwks",
    )

    assert claims["sub"] == "sub-123"
    assert claims["email"] == "user@example.com"
    assert claims["validated"] is True
    assert fake_jwt.called_with[0] == "id-token"
    assert fake_jwt.called_with[1] == "fake-keyset"
    assert fake_jwt.called_with[2]["iss"]["value"] == "https://issuer.example"
    assert fake_jwt.called_with[2]["aud"]["value"] == "client-id"


def test_extract_id_token_claims_raises_value_error_on_decode_error(monkeypatch):
    class FakeJWT:
        def decode(self, id_token, keyset, claims_options):
            raise Exception("bad token")

    monkeypatch.setattr(oauth_service, "_fetch_jwks", lambda jwks_uri: "fake-keyset")
    monkeypatch.setattr(oauth_service, "JsonWebToken", lambda algorithms: FakeJWT())

    with pytest.raises(ValueError, match="Invalid ID token"):
        oauth_service.extract_id_token_claims(
            id_token="id-token",
            client_id="client-id",
            issuer_url="https://issuer.example",
            jwks_uri="https://issuer.example/jwks",
        )


def test_find_or_create_user_from_claims_returns_existing_user_by_sub(db_session):
    user_service = UserService(db_session)
    existing_user = user_service.create_user(
        username="existing-sub-user",
        email="existing-sub@example.com",
        display_name="Existing Sub User",
        password="SecurePass123!",
    )

    identity = OAuthIdentity(
        id="identity-existing-sub",
        user_id=existing_user.id,
        provider="oidc",
        provider_user_id="provider-sub-1",
        provider_email="old@example.com",
        provider_display_name="Old Name",
    )
    db_session.add(identity)
    db_session.commit()

    user, is_new = oauth_service.find_or_create_user_from_claims(
        db=db_session,
        provider="oidc",
        claims={
            "sub": "provider-sub-1",
            "email": "new@example.com",
            "name": "Updated Name",
        },
    )

    refreshed_identity = db_session.execute(
        select(OAuthIdentity).where(OAuthIdentity.id == "identity-existing-sub")
    ).scalar_one()

    assert is_new is False
    assert user.id == existing_user.id
    assert refreshed_identity.provider_email == "new@example.com"
    assert refreshed_identity.provider_display_name == "Updated Name"


def test_find_or_create_user_from_claims_auto_links_existing_user_by_email(db_session):
    user_service = UserService(db_session)
    existing_user = user_service.create_user(
        username="existing-email-user",
        email="existing-email@example.com",
        display_name="Existing Email User",
        password="SecurePass123!",
    )

    user, is_new = oauth_service.find_or_create_user_from_claims(
        db=db_session,
        provider="oidc",
        claims={
            "sub": "provider-sub-2",
            "email": "existing-email@example.com",
            "name": "Existing Email User",
        },
    )

    linked_identity = db_session.execute(
        select(OAuthIdentity).where(
            OAuthIdentity.provider == "oidc",
            OAuthIdentity.provider_user_id == "provider-sub-2",
        )
    ).scalar_one()

    assert is_new is False
    assert user.id == existing_user.id
    assert linked_identity.user_id == existing_user.id


def test_find_or_create_user_from_claims_creates_new_oidc_only_user(db_session):
    user, is_new = oauth_service.find_or_create_user_from_claims(
        db=db_session,
        provider="oidc",
        claims={
            "sub": "provider-sub-3",
            "email": "new-oidc@example.com",
            "name": "New OIDC User",
            "preferred_username": "oidc-new-user",
        },
    )

    linked_identity = db_session.execute(
        select(OAuthIdentity).where(
            OAuthIdentity.provider == "oidc",
            OAuthIdentity.provider_user_id == "provider-sub-3",
        )
    ).scalar_one()

    assert is_new is True
    assert user.email == "new-oidc@example.com"
    assert user.password_hash is None
    assert linked_identity.user_id == user.id