from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    workspace_name: str | None = Field(default=None, min_length=2, max_length=255)


class RegistrationResponse(BaseModel):
    message: str
    email: EmailStr
    requires_email_verification: bool = True


class EmailVerificationRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    password: str = Field(min_length=8, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
