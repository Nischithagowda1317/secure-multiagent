"""Read-only check of DATABASE_URL, required tables, and imported data."""
from __future__ import annotations

from pathlib import Path

from _bootstrap import PROJECT_ROOT  # Adds backend to the import path.
from sqlalchemy import text

from app.services.postgres import create_postgres_engine, validate_schema
from app.services.postgres_runtime_store import RUNTIME_TABLES
from app.services.repository import DataRepository
from app.settings import settings


def main() -> int:
    engine = None
    try:
        schema = validate_schema(settings.database_schema)
        engine = create_postgres_engine(settings.database_url)
        with engine.connect() as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            connection.execute(text("SELECT 1"))
            print("[OK] Database connection successful.")
            tables = set(connection.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = :schema AND table_type = 'BASE TABLE'"
            ), {"schema": schema}).scalars())
            required = {Path(path).stem for path in DataRepository.TABLES.values()} | set(RUNTIME_TABLES)
            missing = sorted(required - tables)
            print(f"[INFO] Found {len(tables)} tables in schema {schema}.")
            if missing:
                print("[FAIL] Missing required tables: " + ", ".join(missing))
                print("Apply supabase/migrations/202609090001_supabase_postgres.sql first.")
                return 2
            print("[OK] All tables required by the backend exist.")
            empty = []
            for table in ("users", "employees", "projects", "tasks"):
                count = connection.execute(text(f'SELECT count(*) FROM "{schema}"."{table}"')).scalar_one()
                print(f"[INFO] {table}: {count:,} rows")
                if count == 0:
                    empty.append(table)
            if empty:
                print("[WARN] Enterprise data is missing. Run backend/scripts/load_supabase.py.")
                return 2
        print("[OK] Database is ready for backend startup.")
        return 0
    except Exception as exc:
        # Classify errors without printing the URL, password, or server details.
        detail = str(exc).lower()
        if "password authentication failed" in detail:
            reason = "Authentication failed. Check the database user and password in DATABASE_URL."
        elif "tenant or user not found" in detail:
            reason = "Pooler user/project not found. Copy the exact user and host from Supabase Connect."
        elif "getaddrinfo" in detail or "could not translate host" in detail:
            reason = "Database hostname could not be resolved. Check the host in DATABASE_URL."
        elif "10013" in detail or "permission denied" in detail:
            reason = "Connection or query was denied. Check network access and database permissions."
        elif "timeout" in detail or "timed out" in detail:
            reason = "Connection timed out. Check network access and whether the Supabase project is running."
        elif isinstance(exc, ValueError):
            reason = "Invalid database configuration. Check DATABASE_URL and DATABASE_SCHEMA."
        else:
            reason = f"Database check failed ({type(exc).__name__}). Check connection settings, SSL and network access."
        print(f"[FAIL] {reason}")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
