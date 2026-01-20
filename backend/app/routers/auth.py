from fastapi import APIRouter, HTTPException, status, Depends
from app.schemas import LoginRequest, TokenResponse
from app.auth import verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login with password and receive JWT token."""
    if not verify_password(request.password):
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
