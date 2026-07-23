from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings


def main() -> int:
    url = make_url(settings.DATABASE_URL)
    safe_url = url.render_as_string(hide_password=True)
    print(f"Checking database: {safe_url}")

    try:
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as connection:
            database = connection.execute(text("select current_database()")).scalar_one()
            user = connection.execute(text("select current_user")).scalar_one()
            print(f"Connected as {user} to database {database}")
        return 0
    except OperationalError as exc:
        print("Database connection failed.")
        print(str(exc).splitlines()[0])
        print("")
        print("Common fixes:")
        print("- Start the local Postgres service: docker compose up -d db")
        print("- If another Postgres is using the configured port, update DATABASE_URL in backend/.env")
        print("- If using the project Docker DB with an old volume, the saved password may differ from docker-compose.yml")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
