"""Import packaged CSV data and optional SQLite runtime state after migration."""
from __future__ import annotations

import argparse
import csv
import sqlite3
from contextlib import closing
from pathlib import Path

from _bootstrap import PROJECT_ROOT
from app.services.postgres import create_postgres_engine, validate_schema
from app.services.postgres_runtime_store import RUNTIME_TABLES
from app.settings import settings
from load_postgresql import iter_source_tables


def import_data(database_url: str, schema: str, dataset_root: Path, runtime_path: Path | None = None):
    from psycopg import sql

    validate_schema(schema)
    sources = list(iter_source_tables(dataset_root))
    if not sources:
        raise ValueError(f"No CSV tables found under {dataset_root}")
    if runtime_path is not None and not runtime_path.is_file():
        raise FileNotFoundError(f"SQLite runtime database does not exist: {runtime_path}")
    engine = create_postgres_engine(database_url)
    loaded = []
    try:
        with closing(engine.raw_connection()) as raw:
            connection = raw.driver_connection
            # The entire import commits together, including deferred foreign keys.
            with connection.transaction(), connection.cursor() as cursor:
                cursor.execute("SET CONSTRAINTS ALL DEFERRED")
                tables = [name for name, _ in sources]
                if runtime_path is not None:
                    tables.extend(RUNTIME_TABLES)
                # Refuse existing data before writing anything. No DROP/TRUNCATE.
                for table in tables:
                    cursor.execute(sql.SQL("SELECT 1 FROM {}.{} LIMIT 1").format(
                        sql.Identifier(schema), sql.Identifier(table),
                    ))
                    if cursor.fetchone():
                        raise ValueError(f"{schema}.{table} already contains data; import cancelled.")
                for table, path in sources:
                    with path.open(encoding="utf-8-sig", newline="") as source:
                        columns = next(csv.reader(source))
                        source.seek(0)
                        statement = sql.SQL(
                            "COPY {}.{} ({}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
                        ).format(sql.Identifier(schema), sql.Identifier(table),
                                 sql.SQL(", ").join(map(sql.Identifier, columns)))
                        with cursor.copy(statement) as copy:
                            while block := source.read(1024 * 1024):
                                copy.write(block)
                    loaded.append(table)
                if runtime_path is not None:
                    # Read a consistent SQLite snapshot, including committed WAL data.
                    uri = runtime_path.resolve().as_uri() + "?mode=ro"
                    with closing(sqlite3.connect(uri, uri=True)) as source:
                        source.execute("BEGIN")
                        for table in RUNTIME_TABLES:
                            rows = source.execute(f'SELECT * FROM "{table}"')
                            columns = [column[0] for column in rows.description]
                            statement = sql.SQL("COPY {}.{} ({}) FROM STDIN").format(
                                sql.Identifier(schema), sql.Identifier(table),
                                sql.SQL(", ").join(map(sql.Identifier, columns)),
                            )
                            with cursor.copy(statement) as copy:
                                for row in rows:
                                    copy.write_row(row)
                            loaded.append(table)
        print(f"[OK] Imported {len(loaded)} tables into {schema}; transaction committed.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-runtime", action="store_true", help="Copy existing SQLite approvals, chats, audit events and document metadata.")
    parser.add_argument("--runtime-path", type=Path, default=settings.runtime_root / "assistant_runtime.db")
    args = parser.parse_args()
    try:
        import_data(settings.database_url, settings.database_schema, settings.dataset_root,
                    args.runtime_path if args.include_runtime else None)
    except Exception as exc:
        # DB exceptions can contain row data. Print only actionable configuration
        # errors; keep server details and credentials out of console logs.
        if isinstance(exc, (ValueError, FileNotFoundError)):
            raise SystemExit(str(exc)) from None
        raise SystemExit(
            "Import failed and was rolled back. Verify DATABASE_URL, apply the SQL migration "
            "to an empty enterprise_ai schema, and check the source CSV schema. "
            f"Error type: {type(exc).__name__}"
        ) from None
