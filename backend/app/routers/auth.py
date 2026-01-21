from fastapi import APIRouter, HTTPException, status, Depends, Request
from app.schemas import LoginRequest, TokenResponse
from app.auth import verify_password, create_access_token, get_current_user
from app.limiter import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, login_request: LoginRequest):
    """Login with password and receive JWT token."""
    if not verify_password(login_request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    access_token = create_access_token()
    return TokenResponse(access_token=access_token)


@router.get("/verify")
async def verify(user: str = Depends(get_current_user)):
    """Verify token is valid."""
    return {"valid": True}
