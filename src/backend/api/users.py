"""Users API endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.core.auth import decode_token
from backend.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


class UserResponse(BaseModel):
    """User response."""

    id: str
    username: str
    nickname: str
    email: str
    display_name: str


async def get_current_user(request: Request, session: Session = Depends(get_db)):
    """
    Extract user from JWT cookie or Authorization header.
    Returns user or raises 401 if not authenticated.
    """
    try:
        # Try cookie first
        token = request.cookies.get("access_token")
        
        # Try Authorization header if no cookie
        if not token:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )
        
        # Decode token
        payload = decode_token(token)
        
        # Load user from database
        user_service = UserService(session)
        user = user_service.get_user_by_id(payload.user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user = Depends(get_current_user)
) -> UserResponse:
    """
    Get current authenticated user information.
    
    Returns:
        UserResponse with user details
    """
    return UserResponse(
        id=user.id,
        username=user.username,
        nickname=user.nickname,
        email=user.email,
        display_name=user.display_name
    )
