from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import secrets
from app.config import get_settings

settings = get_settings()
security = HTTPBearer()


def verify_password(plain_password: str) -> bool:
    """Verify password against configured password using constant-time comparison."""
    return secrets.compare_digest(plain_password, settings.app_password)


def create_access_token(expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode = {
        "exp": expire,
        "sub": "admin",
        "iss": "yt-to-rss",
        "aud": "yt-to-rss-api",
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def verify_token(token: str) -> bool:
    """Verify JWT token."""
    try:
        jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            audience="yt-to-rss-api",
            issuer="yt-to-rss",
        )
        return True
    except JWTError:
        return False


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Dependency to verify authentication."""
    if not verify_token(credentials.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return "admin"
