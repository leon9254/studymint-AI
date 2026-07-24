from app.services.auth_service import build_registration_response
from app.models.user import User


def test_registration_response_is_user_friendly_for_auto_verified_account() -> None:
    user = User(email="demo@example.com", full_name="Demo User", hashed_password="hash", role="USER", email_verified=True)
    result = build_registration_response(user)

    assert result["requires_email_verification"] is False
    assert "ready to use" in str(result["message"])
