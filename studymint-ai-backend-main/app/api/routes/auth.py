from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    EmailVerificationRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    RegistrationResponse,
    ResetPasswordRequest,
    ResendVerificationRequest,
)
from app.schemas.user import UserRead
from app.services.auth_service import (
    AuthError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    VerificationError,
    authenticate_user,
    build_auth_response,
    register_workspace,
    request_password_reset,
    reset_password,
    resend_verification_email,
    verify_email_token,
)
from app.services.email_service import EmailDeliveryError

router = APIRouter()


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        user = authenticate_user(db, payload)
    except InvalidCredentialsError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    except EmailNotVerifiedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before signing in.",
        )
    return build_auth_response(user)


@router.post("/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = register_workspace(db, payload)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account verification email could not be sent. Please try again later.",
        ) from exc
    if user.email_verified:
        return {
            "message": "Account created. Email delivery is not configured in this environment, so the account was verified automatically.",
            "email": user.email,
            "requires_email_verification": False,
        }
    return {
        "message": "Verification email sent. Check your inbox before signing in.",
        "email": user.email,
        "requires_email_verification": True,
    }


@router.post("/verify-email", response_model=AuthResponse)
def verify_email(payload: EmailVerificationRequest, db: Session = Depends(get_db)):
    try:
        user = verify_email_token(db, payload.token)
    except VerificationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return build_auth_response(user)


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
def resend_verification(payload: ResendVerificationRequest, db: Session = Depends(get_db)):
    try:
        resend_verification_email(db, str(payload.email))
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification email could not be sent. Please try again later.",
        ) from exc


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    try:
        request_password_reset(db, str(payload.email))
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset email could not be sent. Please try again later.",
        ) from exc


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password_route(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        reset_password(db, payload.token, payload.password)
    except VerificationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return current_user
