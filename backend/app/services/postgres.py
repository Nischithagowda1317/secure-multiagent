"""Shared PostgreSQL connection configuration, including Supabase poolers."""
from __future__ import annotations

import re


def validate_schema(schema: str) -> str:
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", schema):
        raise ValueError("DATABASE_SCHEMA must be a lowercase SQL identifier (up to 63 characters).")
    return schema


def create_postgres_engine(database_url: str):
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url

    url = make_url(database_url)
    if url.drivername not in {"postgres", "postgresql", "postgresql+psycopg"}:
        raise ValueError("DATABASE_URL must be a PostgreSQL connection string.")
    url = url.set(drivername="postgresql+psycopg")
    if not url.host or not url.password or "YOUR_" in database_url:
        raise ValueError("Set DATABASE_URL to your PostgreSQL connection string in .env.")
    if url.host.endswith((".supabase.co", ".supabase.com")):
        sslmode = url.query.get("sslmode", "require")
        if sslmode not in {"require", "verify-ca", "verify-full"}:
            raise ValueError("Supabase connections require sslmode=require or certificate verification.")
        url = url.update_query_dict({"sslmode": sslmode})
    return create_engine(
        url, pool_pre_ping=True, pool_size=5, max_overflow=0,
        # Transaction poolers cannot reliably preserve prepared statements.
        connect_args={"prepare_threshold": None, "connect_timeout": 15},
    )
