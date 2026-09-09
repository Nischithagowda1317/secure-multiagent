"""PostgreSQL persistence for the existing runtime workflow operations."""
from __future__ import annotations

import threading
from contextlib import contextmanager

from sqlalchemy import text

from app.services.postgres import create_postgres_engine, validate_schema
from app.services.runtime_store import RuntimeStore
from app.settings import Settings


RUNTIME_TABLES = (
    "runtime_approvals", "uploaded_documents", "audit_events", "chat_history",
    "task_assignment_overrides",
)


class _Result:
    def __init__(self, result):
        self.rowcount = result.rowcount
        self._rows = result.mappings() if result.returns_rows else None

    def fetchone(self):
        return self._rows.fetchone()

    def fetchall(self):
        return self._rows.fetchall()


class _Connection:
    """Bind the store's static qmark SQL through SQLAlchemy; values stay bound.

    Only internal RuntimeStore statements are accepted here. Their SQL contains
    no literal question marks or PostgreSQL question-mark operators.
    """

    def __init__(self, connection):
        self.connection = connection

    def execute(self, statement, parameters=()):
        parts = statement.split("?")
        if len(parts) - 1 != len(parameters):
            raise ValueError("SQL parameter count mismatch")
        query = parts[0] + "".join(
            f":p{i}{part}" for i, part in enumerate(parts[1:])
        )
        values = {f"p{i}": value for i, value in enumerate(parameters)}
        return _Result(self.connection.execute(text(query), values))


class PostgresRuntimeStore(RuntimeStore):
    def __init__(self, settings: Settings):
        self.schema = validate_schema(settings.database_schema)
        self._lock = threading.RLock()
        self.engine = create_postgres_engine(settings.database_url)
        # Schema changes are applied explicitly through the migration SQL.
        try:
            with self.connect() as connection:
                for table in RUNTIME_TABLES:
                    connection.execute(f"SELECT * FROM {table} LIMIT 0")
        except Exception:
            self.engine.dispose()
            raise RuntimeError(
                "Cannot open PostgreSQL runtime tables. Check DATABASE_URL and apply "
                "the SQL files in supabase/migrations before starting the app."
            ) from None

    @contextmanager
    def connect(self):
        with self.engine.begin() as connection:
            # Local to this transaction, so transaction poolers are supported.
            connection.execute(
                text("SELECT set_config('search_path', :schema, true)"),
                {"schema": f'"{self.schema}", pg_catalog'},
            )
            yield _Connection(connection)

    def _lock_approval_transaction(self, connection) -> None:
        # Serialize approval execution even when separate API processes race.
        # This also protects the first override when no task row exists yet.
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(?, 0))",
            (f"{self.schema}:approval_execution",),
        )
