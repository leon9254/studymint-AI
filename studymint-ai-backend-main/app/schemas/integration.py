from pydantic import BaseModel, Field, field_validator


class IntegrationRead(BaseModel):
    id: str
    name: str
    status: str
    description: str
    required_fields: list[str]


class StuviaIntegrationConfigRead(BaseModel):
    provider: str = "stuvia"
    status: str
    connected: bool
    automation_ready: bool = False
    stuvia_email: str = ""
    stuvia_password_configured: bool = False
    n8n_webhook_url: str = ""
    n8n_app_url: str = ""
    n8n_webhook_token_configured: bool = False
    stuvia_credential_name: str = "Stuvia Account"
    browser_publisher_url: str = ""
    auto_publish_enabled: bool = False
    credential_storage: str = "backend_encrypted"


class StuviaIntegrationConfigUpdate(BaseModel):
    stuvia_email: str = Field(default="", max_length=255)
    stuvia_password: str | None = Field(default=None, max_length=1000)
    n8n_webhook_url: str | None = Field(default=None, max_length=1000)
    n8n_app_url: str | None = Field(default=None, max_length=1000)
    n8n_webhook_token: str | None = Field(default=None, max_length=1000)
    stuvia_credential_name: str | None = Field(default=None, max_length=120)
    browser_publisher_url: str | None = Field(default=None, max_length=1000)
    auto_publish_enabled: bool = False

    @field_validator("stuvia_email", "n8n_webhook_url", "n8n_app_url", "browser_publisher_url", "stuvia_credential_name", mode="before")
    @classmethod
    def clean_string(cls, value: object) -> str | None:
        if value is None:
            return None
        return " ".join(str(value or "").split()).strip()


class StuviaInternalCredentialRead(BaseModel):
    provider: str = "stuvia"
    tenant_id: str
    stuvia_email: str
    stuvia_password: str
    auto_publish_enabled: bool
    credential_storage: str = "backend_encrypted"
