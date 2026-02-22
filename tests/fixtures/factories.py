"""Test data factories for generating test data."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import random
import string


class UserFactory:
    """Factory for creating user test data."""

    _counter = 0

    @classmethod
    def build(
        cls,
        username: Optional[str] = None,
        email: Optional[str] = None,
        password: str = "TestPass123!",
        display_name: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Build user data dictionary."""
        cls._counter += 1
        
        if username is None:
            username = f"testuser{cls._counter}"
        
        if email is None:
            email = f"{username}@example.com"
        
        if display_name is None:
            display_name = f"Test User {cls._counter}"
        
        return {
            "username": username,
            "email": email,
            "password": password,
            "display_name": display_name,
            **kwargs
        }

    @classmethod
    def build_invalid(cls, field: str) -> Dict[str, Any]:
        """Build user data with specific invalid field."""
        base = cls.build()
        
        invalid_values = {
            "username": {
                "empty": "",
                "too_short": "ab",
                "too_long": "a" * 300,
                "special_chars": "user@name",
                "sql_injection": "admin'--",
                "xss": "<script>alert('xss')</script>",
            },
            "email": {
                "empty": "",
                "no_at": "notanemail",
                "no_domain": "user@",
                "invalid": "user @example.com",
            },
            "password": {
                "empty": "",
                "too_short": "123",
                "too_long": "a" * 1000,
            }
        }
        
        if field in invalid_values:
            for variant, value in invalid_values[field].items():
                data = base.copy()
                data[field] = value
                yield variant, data

    @classmethod
    def build_batch(cls, count: int) -> list[Dict[str, Any]]:
        """Build multiple users."""
        return [cls.build() for _ in range(count)]


class ProjectFactory:
    """Factory for creating project test data."""

    _counter = 0

    @classmethod
    def build(
        cls,
        name: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Build project data dictionary."""
        cls._counter += 1
        
        if name is None:
            name = f"Test Project {cls._counter}"
        
        if description is None:
            description = f"Description for test project {cls._counter}"
        
        return {
            "name": name,
            "description": description,
            **kwargs
        }

    @classmethod
    def build_with_long_name(cls) -> Dict[str, Any]:
        """Build project with very long name."""
        return cls.build(
            name="A" * 255,
            description="Long name test"
        )

    @classmethod
    def build_with_special_chars(cls) -> Dict[str, Any]:
        """Build project with special characters."""
        return cls.build(
            name="Test!@#$% Project",
            description="Special chars test"
        )

    @classmethod
    def build_with_unicode(cls) -> Dict[str, Any]:
        """Build project with unicode characters."""
        return cls.build(
            name="プロジェクト 测试 🚀",
            description="Unicode test"
        )

    @classmethod
    def build_batch(cls, count: int) -> list[Dict[str, Any]]:
        """Build multiple projects."""
        return [cls.build() for _ in range(count)]


class APIKeyFactory:
    """Factory for creating API key test data."""

    _counter = 0

    @classmethod
    def build(
        cls,
        name: Optional[str] = None,
        expires_at: Optional[str] = None,
        scopes: Optional[list[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Build API key data dictionary."""
        cls._counter += 1
        
        if name is None:
            name = f"Test API Key {cls._counter}"
        
        data = {
            "name": name,
            **kwargs
        }
        
        if expires_at is not None:
            data["expires_at"] = expires_at
        
        if scopes is not None:
            data["scopes"] = scopes
        
        return data

    @classmethod
    def build_with_expiration(cls, days: int = 30) -> Dict[str, Any]:
        """Build API key with expiration date."""
        expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat()
        return cls.build(expires_at=expires_at)

    @classmethod
    def build_expired(cls) -> Dict[str, Any]:
        """Build API key that's already expired."""
        expires_at = (datetime.utcnow() - timedelta(days=1)).isoformat()
        return cls.build(expires_at=expires_at)

    @classmethod
    def build_with_scopes(cls, scopes: list[str]) -> Dict[str, Any]:
        """Build API key with specific scopes."""
        return cls.build(scopes=scopes)


class ModelFactory:
    """Factory for creating model file test data."""

    _counter = 0

    @classmethod
    def build_file_data(
        cls,
        filename: Optional[str] = None,
        content_type: str = "model/stl",
        size: int = 1024,
    ) -> tuple[str, bytes, str]:
        """Build file upload data (filename, content, content_type)."""
        cls._counter += 1
        
        if filename is None:
            filename = f"test_model_{cls._counter}.stl"
        
        # Generate fake binary content
        content = b"BINARY_STL_DATA" + (b"X" * (size - 15))
        
        return filename, content, content_type

    @classmethod
    def build_invalid_file(cls, issue: str):
        """Build invalid file data for testing."""
        issues = {
            "wrong_type": ("malicious.exe", b"MALWARE", "application/exe"),
            "too_large": ("huge.stl", b"X" * (100 * 1024 * 1024), "model/stl"),
            "empty": ("empty.stl", b"", "model/stl"),
            "path_traversal": ("../../../etc/passwd", b"DATA", "model/stl"),
            "null_bytes": ("test\x00.stl", b"DATA", "model/stl"),
        }
        
        return issues.get(issue, cls.build_file_data())


class BoundaryValueFactory:
    """Factory for generating boundary value test cases."""

    @staticmethod
    def string_boundaries(max_length: int = 255) -> list[tuple[str, str]]:
        """Generate string boundary test cases."""
        return [
            ("empty", ""),
            ("single_char", "a"),
            ("min_valid", "abc"),  # Assuming min is 3
            ("mid_length", "a" * (max_length // 2)),
            ("max_valid", "a" * max_length),
            ("over_max", "a" * (max_length + 1)),
            ("way_over", "a" * (max_length * 2)),
        ]

    @staticmethod
    def number_boundaries() -> list[tuple[str, int]]:
        """Generate number boundary test cases."""
        return [
            ("zero", 0),
            ("negative", -1),
            ("small_positive", 1),
            ("medium", 1000),
            ("large", 999999),
            ("int_min", -2147483648),
            ("int_max", 2147483647),
            ("overflow", 2147483648),
        ]

    @staticmethod
    def date_boundaries() -> list[tuple[str, str]]:
        """Generate date boundary test cases."""
        now = datetime.utcnow()
        return [
            ("past", (now - timedelta(days=365)).isoformat()),
            ("yesterday", (now - timedelta(days=1)).isoformat()),
            ("now", now.isoformat()),
            ("tomorrow", (now + timedelta(days=1)).isoformat()),
            ("future", (now + timedelta(days=365)).isoformat()),
            ("far_future", (now + timedelta(days=3650)).isoformat()),
        ]


class RandomDataFactory:
    """Factory for generating random test data."""

    @staticmethod
    def random_string(length: int = 10) -> str:
        """Generate random alphanumeric string."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    @staticmethod
    def random_email() -> str:
        """Generate random email address."""
        username = RandomDataFactory.random_string(8)
        domain = RandomDataFactory.random_string(6)
        return f"{username}@{domain}.com"

    @staticmethod
    def random_username() -> str:
        """Generate random username."""
        return RandomDataFactory.random_string(12).lower()

    @staticmethod
    def random_password() -> str:
        """Generate random secure password."""
        chars = string.ascii_letters + string.digits + "!@#$%^&*()"
        return ''.join(random.choices(chars, k=16))


# Convenience function for tests
def create_test_user(**overrides) -> Dict[str, Any]:
    """Create test user with overrides."""
    return UserFactory.build(**overrides)


def create_test_project(**overrides) -> Dict[str, Any]:
    """Create test project with overrides."""
    return ProjectFactory.build(**overrides)


def create_test_api_key(**overrides) -> Dict[str, Any]:
    """Create test API key with overrides."""
    return APIKeyFactory.build(**overrides)
