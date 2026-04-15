"""Authentication utilities for token handling."""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from fastapi import HTTPException, status
from pydantic import BaseModel

# JWT Configuration
JWT_SECRET = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


class TokenPayload(BaseModel):
    """JWT token payload."""

    user_id: str
    username: str
    exp: int  # Expiration timestamp


class Token(BaseModel):
    """Token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds


def create_access_token(user_id: str, username: str) -> Token:
    """Create JWT access token.
    
    Args:
        user_id: User ID
        username: Username
        
    Returns:
        Token with access_token and expiration
    """
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": int(exp.timestamp()),
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    expires_in = int((exp - now).total_seconds())
    
    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
    )


def decode_token(token: str) -> TokenPayload:
    """Decode and validate JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenPayload with user info
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

