import smtplib
import ssl
from html import escape
from email.message import EmailMessage

from app.core.config import settings


class EmailDeliveryError(RuntimeError):
    pass


def _smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USERNAME and settings.SMTP_PASSWORD and settings.SMTP_FROM_EMAIL)


def _send_message(message: EmailMessage) -> None:
    if settings.SMTP_USE_SSL:
        context = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context, timeout=30) as server:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailDeliveryError("SMTP email delivery failed") from exc
        return

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
            if settings.SMTP_USE_STARTTLS:
                server.starttls(context=ssl.create_default_context())
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError("SMTP email delivery failed") from exc


def send_verification_email(email: str, full_name: str, verification_url: str) -> None:
    if not _smtp_configured():
        raise EmailDeliveryError("SMTP email delivery is not configured")

    safe_name = escape(full_name.strip() or "there")
    safe_url = escape(verification_url)
    expiry_hours = settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS

    message = EmailMessage()
    message["Subject"] = "Verify your StudyMint AI account"
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = email
    message.set_content(
        "\n".join(
            [
                f"Hi {full_name},",
                "",
                "Welcome to StudyMint AI. Please verify your email address so you can start creating structured study documents, reviewing PDF previews, and exporting polished learning materials.",
                "",
                "Verify your account:",
                verification_url,
                "",
                f"This secure link expires in {expiry_hours} hours.",
                "",
                "If you did not create this account, you can ignore this email.",
                "",
                "StudyMint AI",
            ]
        )
    )
    message.add_alternative(
        f"""\
<!doctype html>
<html>
  <body style="margin:0;background:#f2f5f1;padding:32px 16px;font-family:Arial,Helvetica,sans-serif;color:#172033;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;margin:0 auto;background:#ffffff;border:1px solid #dfe7df;border-radius:14px;overflow:hidden;">
      <tr>
        <td style="background:#0f2f2b;padding:28px 32px;color:#ffffff;">
          <div style="font-size:13px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#9ee6d8;">StudyMint AI</div>
          <h1 style="margin:10px 0 0;font-size:28px;line-height:1.2;font-weight:700;">Verify your email address</h1>
        </td>
      </tr>
      <tr>
        <td style="padding:32px;">
          <p style="margin:0 0 16px;font-size:16px;line-height:1.65;">Hi {safe_name},</p>
          <p style="margin:0 0 22px;font-size:16px;line-height:1.65;color:#39453f;">
            Welcome to StudyMint AI. Verify your email to start turning course material, notes, and outlines into structured study documents with PDF-ready previews and exports.
          </p>
          <a href="{safe_url}" style="display:inline-block;background:#0f766e;color:#ffffff;text-decoration:none;font-size:15px;font-weight:700;padding:13px 22px;border-radius:8px;">
            Verify email
          </a>
          <p style="margin:24px 0 0;font-size:13px;line-height:1.6;color:#66736c;">
            This secure link expires in {expiry_hours} hours. If the button does not work, copy and paste this link into your browser:
          </p>
          <p style="margin:8px 0 0;font-size:13px;line-height:1.6;word-break:break-all;color:#0f766e;">{safe_url}</p>
        </td>
      </tr>
      <tr>
        <td style="border-top:1px solid #e6ece6;padding:20px 32px;background:#fbfcfb;">
          <p style="margin:0;font-size:12px;line-height:1.6;color:#6b756f;">
            If you did not create a StudyMint AI account, you can safely ignore this email.
          </p>
        </td>
      </tr>
    </table>
  </body>
</html>
""",
        subtype="html",
    )
    _send_message(message)


def send_password_reset_email(email: str, full_name: str, reset_url: str) -> None:
    if not _smtp_configured():
        raise EmailDeliveryError("SMTP email delivery is not configured")

    safe_name = escape(full_name.strip() or "there")
    safe_url = escape(reset_url)
    expiry_minutes = settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES

    message = EmailMessage()
    message["Subject"] = "Reset your StudyMint AI password"
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = email
    message.set_content(
        "\n".join(
            [
                f"Hi {full_name},",
                "",
                "We received a request to reset your StudyMint AI password.",
                "",
                "Create a new password using this secure link:",
                reset_url,
                "",
                f"This link expires in {expiry_minutes} minutes.",
                "",
                "If you did not request this reset, you can ignore this email and your password will stay the same.",
                "",
                "StudyMint AI",
            ]
        )
    )
    message.add_alternative(
        f"""\
<!doctype html>
<html>
  <body style="margin:0;background:#f2f5f1;padding:32px 16px;font-family:Arial,Helvetica,sans-serif;color:#172033;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;margin:0 auto;background:#ffffff;border:1px solid #dfe7df;border-radius:14px;overflow:hidden;">
      <tr>
        <td style="background:#111827;padding:28px 32px;color:#ffffff;">
          <div style="font-size:13px;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#9ee6d8;">StudyMint AI</div>
          <h1 style="margin:10px 0 0;font-size:28px;line-height:1.2;font-weight:700;">Reset your password</h1>
        </td>
      </tr>
      <tr>
        <td style="padding:32px;">
          <p style="margin:0 0 16px;font-size:16px;line-height:1.65;">Hi {safe_name},</p>
          <p style="margin:0 0 22px;font-size:16px;line-height:1.65;color:#39453f;">
            Use the secure link below to create a new password and return to your StudyMint AI document workspace.
          </p>
          <a href="{safe_url}" style="display:inline-block;background:#0f766e;color:#ffffff;text-decoration:none;font-size:15px;font-weight:700;padding:13px 22px;border-radius:8px;">
            Reset password
          </a>
          <p style="margin:24px 0 0;font-size:13px;line-height:1.6;color:#66736c;">
            This secure link expires in {expiry_minutes} minutes. If the button does not work, copy and paste this link into your browser:
          </p>
          <p style="margin:8px 0 0;font-size:13px;line-height:1.6;word-break:break-all;color:#0f766e;">{safe_url}</p>
        </td>
      </tr>
      <tr>
        <td style="border-top:1px solid #e6ece6;padding:20px 32px;background:#fbfcfb;">
          <p style="margin:0;font-size:12px;line-height:1.6;color:#6b756f;">
            If you did not request this reset, you can safely ignore this email and your password will stay the same.
          </p>
        </td>
      </tr>
    </table>
  </body>
</html>
""",
        subtype="html",
    )
    _send_message(message)
