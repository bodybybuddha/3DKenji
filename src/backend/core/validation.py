"""Form validation utilities and schemas."""

from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, validator, ValidationError
import re


# Username validation
def validate_username(username: str) -> str:
    """Validate username format."""
    if not username or len(username) < 3:
        raise ValueError("Username must be at least 3 characters")
    if len(username) > 32:
        raise ValueError("Username must be at most 32 characters")
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
    return username


# Email validation
def validate_email(email: str) -> str:
    """Validate email format."""
    if not email or len(email) < 5:
        raise ValueError("Email is required")
    if len(email) > 254:
        raise ValueError("Email is too long")
    if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        raise ValueError("Invalid email format")
    return email


# Password validation
def validate_password(password: str) -> str:
    """Validate password requirements."""
    if not password:
        raise ValueError("Password is required")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(password) > 128:
        raise ValueError("Password must be at most 128 characters")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one digit")
    return password


# Form validation schemas
class LoginRequest(BaseModel):
    """Login form validation."""
    username_or_email: str = Field(..., min_length=1, max_length=254)
    password: str = Field(..., min_length=1)

    @validator("username_or_email")
    def validate_username_or_email(cls, v):
        if "@" in v:
            # Validate as email
            if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v):
                raise ValueError("Invalid email format")
        else:
            # Validate as username
            if len(v) < 3:
                raise ValueError("Username must be at least 3 characters")
            if not re.match(r"^[a-zA-Z0-9_-]+$", v):
                raise ValueError("Invalid username format")
        return v


class RegisterRequest(BaseModel):
    """Registration form validation."""
    username: str = Field(..., min_length=3, max_length=32)
    email: str = Field(...)
    display_name: Optional[str] = Field(None, max_length=100)
    password: str = Field(...)
    password_confirm: str = Field(...)

    @validator("username")
    def validate_username_field(cls, v):
        return validate_username(v)

    @validator("email")
    def validate_email_field(cls, v):
        return validate_email(v)

    @validator("password")
    def validate_password_field(cls, v):
        return validate_password(v)

    @validator("password_confirm")
    def validate_password_match(cls, v, values):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v


class CreateProjectRequest(BaseModel):
    """Project creation form validation."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    visibility: str = Field(default="private")

    @validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Project name cannot be empty")
        if len(v.strip()) > 255:
            raise ValueError("Project name is too long")
        return v.strip()

    @validator("visibility")
    def validate_visibility(cls, v):
        if v not in ["private", "public"]:
            raise ValueError("Visibility must be either 'private' or 'public'")
        return v


class CreateAPIKeyRequest(BaseModel):
    """API key creation form validation."""
    name: str = Field(..., min_length=1, max_length=255)
    scopes: list[str] = Field(default=["read:models"])
    expiry_days: Optional[int] = Field(None)

    @validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Key name cannot be empty")
        return v.strip()

    @validator("scopes")
    def validate_scopes(cls, v):
        valid_scopes = [
            "read:models",
            "write:models",
            "read:projects",
            "write:projects",
            "read:settings",
            "write:settings",
        ]
        if not v:
            raise ValueError("At least one scope must be selected")
        for scope in v:
            if scope not in valid_scopes:
                raise ValueError(f"Invalid scope: {scope}")
        return v

    @validator("expiry_days")
    def validate_expiry(cls, v):
        if v is not None:
            if v < 1 or v > 36500:  # 100 years max
                raise ValueError("Expiry must be between 1 and 36500 days")
        return v


class UpdateProfileRequest(BaseModel):
    """User profile update validation."""
    email: Optional[str] = Field(None)
    display_name: Optional[str] = Field(None, max_length=100)

    @validator("email")
    def validate_email_field(cls, v):
        if v is not None:
            validate_email(v)
        return v


class ChangePasswordRequest(BaseModel):
    """Password change validation."""
    current_password: str = Field(...)
    new_password: str = Field(...)
    new_password_confirm: str = Field(...)

    @validator("new_password")
    def validate_new_password(cls, v):
        return validate_password(v)

    @validator("new_password_confirm")
    def validate_passwords_match(cls, v, values):
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("New passwords do not match")
        return v


class ModelUploadRequest(BaseModel):
    """Model file upload validation."""
    project_id: str = Field(...)
    model_name: str = Field(..., min_length=1, max_length=255)
    framework: Optional[str] = Field(None)
    version: Optional[str] = Field(None, max_length=50)

    @validator("model_name")
    def validate_model_name(cls, v):
        if not v.strip():
            raise ValueError("Model name cannot be empty")
        return v.strip()

    @validator("framework")
    def validate_framework(cls, v):
        if v is not None:
            valid_frameworks = [
                "pytorch",
                "tensorflow",
                "onnx",
                "sklearn",
                "other",
            ]
            if v not in valid_frameworks:
                raise ValueError(f"Invalid framework: {v}")
        return v


class ValidationErrorResponse(BaseModel):
    """Standard validation error response."""
    success: bool = False
    errors: Dict[str, list[str]]
    message: str = "Validation failed"


def format_validation_errors(validation_error: ValidationError) -> Dict[str, list[str]]:
    """Convert Pydantic ValidationError to field-level error dict."""
    errors: Dict[str, list[str]] = {}
    for error in validation_error.errors():
        field = error["loc"][0] if error["loc"] else "general"
        message = error["msg"]
        if field not in errors:
            errors[field] = []
        errors[field].append(message)
    return errors
