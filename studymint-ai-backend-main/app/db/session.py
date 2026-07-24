from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base

import app.models  # noqa: F401

_database_path = Path(__file__).resolve().parents[1] / "studymint.db"
_database_url = settings.DATABASE_URL
if _database_url == "sqlite:///./studymint.db":
    _database_url = f"sqlite:///{_database_path.as_posix()}"

engine = create_engine(_database_url, pool_pre_ping=True)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
