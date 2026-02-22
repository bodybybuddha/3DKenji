"""Shared fixtures and test data for validation tests."""

import pytest
import httpx
import os
import uuid


@pytest.fixture
def client():
    """HTTP client for API testing."""
    base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    return httpx.Client(base_url=base_url)


@pytest.fixture
def auth_client(client):
    """Authenticated HTTP client with unique user per test."""
    unique_id = str(uuid.uuid4())[:8]
    username = f"valuser_{unique_id}"
    email = f"valuser_{unique_id}@example.com"
    password = "SecurePass123!"
    
    # Try to register
    response = client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
        "display_name": f"Validation User {unique_id}"
    })
    
    if response.status_code == 201:
        token = response.json()["access_token"]
    else:
        # If registration fails, try login
        login_response = client.post("/api/v1/auth/login", json={
            "username": username,
            "password": password
        })
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
        else:
            pytest.fail(f"Failed to authenticate test user: {login_response.text}")
    
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.fixture
def auth_client_secondary(client):
    """Second authenticated HTTP client for multi-user tests."""
    unique_id = str(uuid.uuid4())[:8]
    username = f"valuser2_{unique_id}"
    email = f"valuser2_{unique_id}@example.com"
    password = "SecurePass456!"
    
    response = client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
        "display_name": f"Validation User 2 {unique_id}"
    })
    
    if response.status_code == 201:
        token = response.json()["access_token"]
        secondary_client = httpx.Client(
            base_url=os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
        )
        secondary_client.headers["Authorization"] = f"Bearer {token}"
        return secondary_client
    else:
        pytest.fail(f"Failed to create secondary test user: {response.text}")


# Test Data Collections

INVALID_USERNAMES = [
    ("", "required"),
    (" ", "required"),
    ("a", "too short"),
    ("ab", "too short"),  # If min is 3
    ("a" * 300, "too long"),
    ("user name", "invalid"),
    ("user@name", "invalid"),
    ("user#name", "invalid"),
    ("<script>", "invalid"),
    ("admin'--", "invalid"),
    ("test\x00user", "invalid"),  # Null byte
    ("../../../etc", "invalid"),
    ("user; DROP TABLE users;--", "invalid"),
]

VALID_USERNAMES = [
    "validuser",
    "user123",
    "user_name",
    "USER",
    "a" * 20,  # Mid-length
]

INVALID_EMAILS = [
    ("", "required"),
    ("notanemail", "invalid"),
    ("@example.com", "invalid"),
    ("user@", "invalid"),
    ("user @example.com", "invalid"),
    ("user@.com", "invalid"),
    ("user..name@example.com", "invalid"),
    ("<script>@example.com", "invalid"),
    ("a" * 300 + "@example.com", "too long"),
]

VALID_EMAILS = [
    "user@example.com",
    "user.name@example.com",
    "user+tag@example.co.uk",
    "123@example.com",
    "user@subdomain.example.com",
]

INVALID_PASSWORDS = [
    ("", "required"),
    ("123", "too short"),
    ("short", "too short"),
    ("a" * 1000, "too long"),
    ("simple", "too weak"),  # Depending on requirements
]

VALID_PASSWORDS = [
    "SecurePass123!",
    "MyP@ssw0rd",
    "Complex!ty1",
    "a" * 50,  # If length is the only requirement
]

XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert('XSS')>",
    "<svg onload=alert('XSS')>",
    "javascript:alert('XSS')",
    "<iframe src='javascript:alert(\"XSS\")'></iframe>",
    "<body onload=alert('XSS')>",
    "<input onfocus=alert('XSS') autofocus>",
    "'\"><script>alert(String.fromCharCode(88,83,83))</script>",
]

SQL_INJECTION_PAYLOADS = [
    "' OR '1'='1",
    "'; DROP TABLE users;--",
    "admin'--",
    "1' OR '1' = '1",
    "1'; DELETE FROM users WHERE 'a' = 'a",
    "' UNION SELECT * FROM users--",
    "1' AND 1=0 UNION ALL SELECT 'admin', 'password'--",
]

PATH_TRAVERSAL_PAYLOADS = [
    "../../../etc/passwd",
    "..\\..\\..\\windows\\system32\\config\\sam",
    "....//....//....//etc/passwd",
    "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
]

UNICODE_TEST_STRINGS = [
    "日本語",
    "Ñoño",
    "Москва",
    "مرحبا",
    "😀🚀🎉",
    "𝕳𝖊𝖑𝖑𝖔",  # Mathematical bold
    "\u200B",  # Zero-width space
    "café",
    "naïve",
]

SPECIAL_CHARACTERS = [
    "!@#$%^&*()",
    "[]{}|\\:;\"'<>,.?/",
    "~`",
    "\n\r\t",
    "\x00\x01",  # Control characters
]

BOUNDARY_NUMBERS = [
    -2147483648,  # INT_MIN
    2147483647,   # INT_MAX
    0,
    -1,
    1,
    9999999999999999,  # Large number
]

INVALID_DATES = [
    "not-a-date",
    "2024-13-01",  # Invalid month
    "2024-02-30",  # Invalid day
    "2024/02/01",  # Wrong format
    "01-02-2024",  # Wrong format
]

VALID_DATES = [
    "2024-01-01",
    "2024-12-31",
    "2024-02-29",  # Leap year
    "2024-01-01T00:00:00Z",
    "2024-01-01T12:34:56+00:00",
]


@pytest.fixture
def invalid_usernames():
    """Fixture providing invalid username test cases."""
    return INVALID_USERNAMES


@pytest.fixture
def valid_usernames():
    """Fixture providing valid username test cases."""
    return VALID_USERNAMES


@pytest.fixture
def invalid_emails():
    """Fixture providing invalid email test cases."""
    return INVALID_EMAILS


@pytest.fixture
def valid_emails():
    """Fixture providing valid email test cases."""
    return VALID_EMAILS


@pytest.fixture
def xss_payloads():
    """Fixture providing XSS attack payloads."""
    return XSS_PAYLOADS


@pytest.fixture
def sql_injection_payloads():
    """Fixture providing SQL injection payloads."""
    return SQL_INJECTION_PAYLOADS
