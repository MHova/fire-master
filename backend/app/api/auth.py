from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import create_access_token, verify_password
from app.core.config import Settings, get_settings
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, settings: Settings = Depends(get_settings)):
    if body.username != settings.AUTH_USERNAME or not verify_password(
        body.password, settings.AUTH_PASSWORD_HASH
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    token = create_access_token(body.username, settings)
    return TokenResponse(access_token=token)
