from app.core.config import Settings


def test_settings_default_database_url_is_sqlite_for_local_dev() -> None:
    settings = Settings(_env_file=None)

    assert settings.DATABASE_URL.startswith("sqlite://")
    assert "studymint.db" in settings.DATABASE_URL
