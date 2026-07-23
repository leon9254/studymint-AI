import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.secret_box import decrypt_secret, encrypt_secret
from app.models.integration import IntegrationConfig
from app.schemas.integration import IntegrationRead, StuviaIntegrationConfigRead, StuviaIntegrationConfigUpdate, StuviaInternalCredentialRead


STUVIA_PROVIDER = "stuvia"
STUVIA_TOPIC_HISTORY_LIMIT = 2000


def _valid_optional_url(value: str, field_name: str) -> str:
    cleaned = " ".join(str(value or "").split()).strip()
    if not cleaned:
        return ""

    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field_name} must be a valid http(s) URL")
    return cleaned


def _stuvia_defaults() -> dict:
    return {
        "n8n_webhook_url": settings.N8N_STUVIA_WEBHOOK_URL,
        "n8n_webhook_token": settings.N8N_STUVIA_WEBHOOK_TOKEN,
        "n8n_app_url": "",
        "stuvia_credential_name": "Stuvia Account",
        "browser_publisher_url": "",
        "auto_publish_enabled": False,
        "stuvia_email": "",
        "stuvia_password_configured": False,
        "stuvia_password_encrypted": "",
        "topic_pool_entries": [],
        "topic_pool_profile_url": "",
        "topic_pool_scraped_at": "",
        "used_topic_entries": [],
        "used_topic_keys": [],
    }


def _get_config(db: Session, tenant_id: str, provider: str) -> IntegrationConfig | None:
    return db.scalar(
        select(IntegrationConfig)
        .where(IntegrationConfig.tenant_id == tenant_id, IntegrationConfig.provider == provider)
        .order_by(IntegrationConfig.updated_at.desc())
    )


def stuvia_connection_settings(db: Session, tenant_id: str) -> dict:
    current = _stuvia_defaults()
    config = _get_config(db, tenant_id, STUVIA_PROVIDER)
    if config and isinstance(config.settings, dict):
        current.update(config.settings)
    return current


def _stuvia_topic_key(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
    return re.sub(r"\s+", " ", cleaned).strip()[:180]


def _specific_stuvia_topic_key(value: str) -> bool:
    key = _stuvia_topic_key(value)
    if not key:
        return False
    if re.search(r"\b(?:ati|hesi|nclex|nurs|nur|nr|wgu)\b", key):
        return True
    return bool(re.search(r"\b[a-z]{2,}\s*\d{2,}\b|\d", key))


def stuvia_topic_identity_keys(topic: dict[str, Any]) -> set[str]:
    title_key = _stuvia_topic_key(str(topic.get("title") or ""))
    topic_key = _stuvia_topic_key(str(topic.get("topic") or ""))
    keys = {title_key} if title_key else set()
    if topic_key and _specific_stuvia_topic_key(topic_key):
        keys.add(topic_key)
    return keys


def _used_topic_keys(settings_payload: dict) -> set[str]:
    keys: set[str] = set()
    entries = settings_payload.get("used_topic_entries", [])
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict):
                keys.update(stuvia_topic_identity_keys(entry))
                entry_key = _stuvia_topic_key(str(entry.get("key") or ""))
                if _specific_stuvia_topic_key(entry_key):
                    keys.add(entry_key)
    if not keys:
        keys = {
            _stuvia_topic_key(key)
            for key in settings_payload.get("used_topic_keys", [])
            if isinstance(key, str) and key.strip()
        }
    return {key for key in keys if key}


def filter_new_stuvia_topic_candidates(
    topics: list[dict[str, Any]],
    used_keys: set[str],
    limit: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_keys = {_stuvia_topic_key(key) for key in used_keys if key}

    for topic in topics:
        topic_keys = stuvia_topic_identity_keys(topic)
        if not topic_keys or topic_keys & seen_keys:
            continue
        selected.append(topic)
        seen_keys.update(topic_keys)
        if len(selected) >= limit:
            break

    return selected


def filter_unused_stuvia_topics(db: Session, tenant_id: str, topics: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    current = stuvia_connection_settings(db, tenant_id)
    return filter_new_stuvia_topic_candidates(topics, _used_topic_keys(current), limit)


def _save_stuvia_settings(db: Session, tenant_id: str, current: dict) -> None:
    config = _get_config(db, tenant_id, STUVIA_PROVIDER)
    webhook_url = str(current.get("n8n_webhook_url") or "")
    if config is None:
        config = IntegrationConfig(
            tenant_id=tenant_id,
            provider=STUVIA_PROVIDER,
            status="CONNECTED" if webhook_url else "PENDING",
            settings=current,
        )
        db.add(config)
    else:
        config.status = "CONNECTED" if webhook_url else "PENDING"
        config.settings = dict(current)
    db.commit()


def cached_stuvia_topics(db: Session, tenant_id: str, profile_url: str, limit: int) -> list[dict[str, Any]]:
    current = stuvia_connection_settings(db, tenant_id)
    if str(current.get("topic_pool_profile_url") or "") != profile_url:
        return []

    pool = current.get("topic_pool_entries", [])
    if not isinstance(pool, list):
        return []
    topics = [topic for topic in pool if isinstance(topic, dict)]
    return filter_new_stuvia_topic_candidates(topics, _used_topic_keys(current), limit)


def remember_stuvia_topic_pool(db: Session, tenant_id: str, profile_url: str, topics: list[dict[str, Any]]) -> None:
    if not topics:
        return

    current = stuvia_connection_settings(db, tenant_id)
    entries: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    now = datetime.now(timezone.utc).isoformat()

    for topic in topics:
        if not isinstance(topic, dict):
            continue
        topic_keys = stuvia_topic_identity_keys(topic)
        if not topic_keys or topic_keys & seen_keys:
            continue
        seen_keys.update(topic_keys)
        entries.append(
            {
                "key": sorted(topic_keys)[0],
                "title": str(topic.get("title") or "")[:180],
                "topic": str(topic.get("topic") or "")[:180],
                "source_url": str(topic.get("source_url") or "")[:500],
                "score": topic.get("score", 0),
                "reason": str(topic.get("reason") or "")[:240],
                "cached_at": now,
            }
        )

    current["topic_pool_entries"] = entries[-STUVIA_TOPIC_HISTORY_LIMIT:]
    current["topic_pool_profile_url"] = profile_url
    current["topic_pool_scraped_at"] = now
    _save_stuvia_settings(db, tenant_id, current)


def remember_stuvia_topics(db: Session, tenant_id: str, topics: list[dict[str, Any]]) -> None:
    if not topics:
        return

    current = stuvia_connection_settings(db, tenant_id)
    entries = current.get("used_topic_entries", [])
    if not isinstance(entries, list):
        entries = []

    used_keys = _used_topic_keys(current)
    now = datetime.now(timezone.utc).isoformat()
    for topic in topics:
        topic_keys = stuvia_topic_identity_keys(topic)
        if not topic_keys or topic_keys & used_keys:
            continue
        primary_key = sorted(topic_keys)[0]
        entries.append(
            {
                "key": primary_key,
                "title": str(topic.get("title") or "")[:180],
                "topic": str(topic.get("topic") or "")[:180],
                "source_url": str(topic.get("source_url") or "")[:500],
                "used_at": now,
            }
        )
        used_keys.update(topic_keys)

    current["used_topic_entries"] = entries[-STUVIA_TOPIC_HISTORY_LIMIT:]
    current["used_topic_keys"] = sorted(_used_topic_keys(current))[-STUVIA_TOPIC_HISTORY_LIMIT:]

    _save_stuvia_settings(db, tenant_id, current)


def clear_stuvia_topic_history(db: Session, tenant_id: str) -> None:
    current = stuvia_connection_settings(db, tenant_id)
    current["used_topic_entries"] = []
    current["used_topic_keys"] = []

    _save_stuvia_settings(db, tenant_id, current)


def get_stuvia_connection(db: Session, tenant_id: str) -> StuviaIntegrationConfigRead:
    current = stuvia_connection_settings(db, tenant_id)
    webhook_url = str(current.get("n8n_webhook_url") or "")
    token = str(current.get("n8n_webhook_token") or "")
    automation_ready = bool(webhook_url)
    stuvia_email = str(current.get("stuvia_email") or "")
    password_configured = bool(current.get("stuvia_password_encrypted"))
    connected = automation_ready and bool(stuvia_email) and password_configured
    if connected:
        status_label = "Connected"
    elif automation_ready:
        status_label = "Connect account"
    else:
        status_label = "Automation setup needed"

    return StuviaIntegrationConfigRead(
        status=status_label,
        connected=connected,
        automation_ready=automation_ready,
        stuvia_email=stuvia_email,
        stuvia_password_configured=password_configured,
        n8n_webhook_url=webhook_url,
        n8n_app_url=str(current.get("n8n_app_url") or ""),
        n8n_webhook_token_configured=bool(token),
        stuvia_credential_name=str(current.get("stuvia_credential_name") or "Stuvia Account"),
        browser_publisher_url=str(current.get("browser_publisher_url") or ""),
        auto_publish_enabled=bool(current.get("auto_publish_enabled")),
    )


def update_stuvia_connection(db: Session, tenant_id: str, payload: StuviaIntegrationConfigUpdate) -> StuviaIntegrationConfigRead:
    config = _get_config(db, tenant_id, STUVIA_PROVIDER)
    current = stuvia_connection_settings(db, tenant_id)

    if payload.n8n_webhook_url is not None:
        current["n8n_webhook_url"] = _valid_optional_url(payload.n8n_webhook_url, "n8n webhook URL")
    if payload.n8n_app_url is not None:
        current["n8n_app_url"] = _valid_optional_url(payload.n8n_app_url, "n8n app URL")
    if payload.n8n_webhook_token is not None:
        current["n8n_webhook_token"] = payload.n8n_webhook_token.strip()
    if payload.stuvia_credential_name is not None:
        current["stuvia_credential_name"] = payload.stuvia_credential_name or "Stuvia Account"
    if payload.browser_publisher_url is not None:
        current["browser_publisher_url"] = _valid_optional_url(payload.browser_publisher_url, "browser publisher URL")
    if payload.stuvia_email is not None:
        current["stuvia_email"] = payload.stuvia_email.lower()
    if payload.stuvia_password:
        current["stuvia_password_encrypted"] = encrypt_secret(payload.stuvia_password)
        current["stuvia_password_configured"] = True

    current["auto_publish_enabled"] = bool(payload.auto_publish_enabled)
    webhook_url = str(current.get("n8n_webhook_url") or "")

    if config is None:
        config = IntegrationConfig(
            tenant_id=tenant_id,
            provider=STUVIA_PROVIDER,
            status="CONNECTED" if webhook_url else "PENDING",
            settings=current,
        )
        db.add(config)
    else:
        config.status = "CONNECTED" if webhook_url else "PENDING"
        config.settings = dict(current)

    db.commit()
    return get_stuvia_connection(db, tenant_id)


def get_stuvia_internal_credentials(db: Session, tenant_id: str) -> StuviaInternalCredentialRead:
    current = stuvia_connection_settings(db, tenant_id)
    stuvia_email = str(current.get("stuvia_email") or "")
    stuvia_password = decrypt_secret(str(current.get("stuvia_password_encrypted") or ""))

    if not stuvia_email or not stuvia_password:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stuvia credentials are not configured for this tenant")

    return StuviaInternalCredentialRead(
        tenant_id=tenant_id,
        stuvia_email=stuvia_email,
        stuvia_password=stuvia_password,
        auto_publish_enabled=bool(current.get("auto_publish_enabled")),
    )


def list_integrations(db: Session, tenant_id: str) -> list[IntegrationRead]:
    stuvia_status = get_stuvia_connection(db, tenant_id).status
    return [
        IntegrationRead(
            id="stuvia",
            name="Stuvia",
            status=stuvia_status,
            description="Connect a Stuvia seller account for background publishing automation.",
            required_fields=["Seller email", "Seller password", "Auto-publish setting", "Compliance confirmation"],
        ),
        IntegrationRead(
            id="docsity",
            name="Docsity/DocCity",
            status="Coming soon",
            description="Structure documents for future marketplace upload and metadata review.",
            required_fields=["Account connection", "Course metadata", "Language rules", "Publishing checklist"],
        ),
        IntegrationRead(
            id="other",
            name="Other marketplaces",
            status="Coming soon",
            description="Adapter-ready placeholder for additional document-selling platforms.",
            required_fields=["Adapter type", "Listing metadata", "Export format", "Review policy"],
        ),
    ]
