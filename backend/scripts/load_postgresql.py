from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from _bootstrap import PROJECT_ROOT
from app.settings import settings
from app.services.postgres import create_postgres_engine, validate_schema


def _load_optional_dependencies():
    try:
        from sqlalchemy import text
    except ImportError as exc:
        raise SystemExit(
            "PostgreSQL support is not installed. Run:\n"
            "  pip install -r backend/requirements-postgres.txt"
        ) from exc
    return text


def iter_source_tables(dataset_root: Path):
    core = dataset_root / "core"
    for csv_path in sorted(core.glob("*/*.csv")):
        yield csv_path.stem, csv_path
    raw_agent = dataset_root / "raw_sources" / "agentic_ai_performance_source.csv"
    if raw_agent.exists():
        yield raw_agent.stem, raw_agent


def main(database_url: str, schema: str, replace: bool) -> None:
    text = _load_optional_dependencies()
    validate_schema(schema)
    from sqlalchemy.engine import make_url
    host = make_url(database_url).host or ""
    if host.endswith((".supabase.co", ".supabase.com")) or settings.data_backend == "supabase":
        raise SystemExit("For Supabase, apply supabase/migrations SQL and run backend/scripts/load_supabase.py. This preserves constraints and RLS.")
    dataset_root = (
        PROJECT_ROOT / "datasets" / "Secure_Multi_Agent_Enterprise_Dataset"
    )
    engine = create_postgres_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))

    mode = "replace" if replace else "fail"
    loaded = []
    for table_name, csv_path in iter_source_tables(dataset_root):
        frame = pd.read_csv(csv_path, encoding="utf-8-sig")
        frame.to_sql(
            table_name,
            con=engine,
            schema=schema,
            if_exists=mode,
            index=False,
            chunksize=1000,
            method="multi",
        )
        loaded.append((table_name, len(frame)))
        print(f"[OK] {schema}.{table_name}: {len(frame):,} rows")

    indexes = [
        ("projects", "idx_projects_project_id", "project_id"),
        ("tasks", "idx_tasks_project_id", "project_id"),
        ("employees", "idx_employees_employee_id", "employee_id"),
        ("sales_orders", "idx_sales_orders_region", "region"),
        ("rag_chunks", "idx_rag_chunks_document_id", "document_id"),
    ]
    with engine.begin() as connection:
        for table, index, column in indexes:
            connection.execute(
                text(
                    f'CREATE INDEX IF NOT EXISTS "{index}" '
                    f'ON "{schema}"."{table}" ("{column}")'
                )
            )
    print(f"\nLoaded {len(loaded)} tables into PostgreSQL.")
    print("To make the application use PostgreSQL, set DATA_BACKEND=postgres in .env.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load all curated enterprise CSV tables into PostgreSQL."
    )
    parser.add_argument(
        "--database-url",
        default=settings.database_url,
    )
    parser.add_argument("--schema", default=settings.database_schema)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace existing tables. Without this flag the loader stops if a table exists.",
    )
    args = parser.parse_args()
    main(args.database_url, args.schema, args.replace)
