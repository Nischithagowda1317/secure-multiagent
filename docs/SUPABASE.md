# Supabase PostgreSQL setup

Supabase stores enterprise tables plus approvals, chats, audit events, task
reassignments and uploaded-document metadata. FastAPI still handles login and
RBAC. Upload files, extracted text, model files and the RAG index remain on disk;
retain `runtime/uploads` and the existing local paths when migrating runtime data.

1. Install dependencies:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
   ```

2. Open your Supabase project's **Connect** panel. Copy its **Session pooler**
   PostgreSQL URI (port 5432, IPv4 compatible) into `.env`:

   ```dotenv
   DATA_BACKEND=supabase
   DATABASE_URL=postgresql://postgres.YOUR_PROJECT_REF:YOUR_URL_ENCODED_PASSWORD@YOUR_POOLER_HOST:5432/postgres?sslmode=require
   DATABASE_SCHEMA=enterprise_ai
   RUNTIME_BACKEND=auto
   ```

   Use the exact host and user shown by Supabase. Percent-encode special password
   characters such as `@`, `#`, `/` and `%`. This is the database password, not an
   anon/publishable/service API key. Keep the URI in the backend `.env` only.
   `postgresql+psycopg://` and `postgres://` URIs also work. Direct connections work
   when the host has IPv6 connectivity. The app disables prepared statements for
   compatibility with transaction poolers; use the session URI for imports.
   See [Supabase connection documentation](https://supabase.com/docs/guides/database/connecting-to-postgres).

3. In Supabase **SQL Editor**, run
   [`202609090001_supabase_postgres.sql`](../supabase/migrations/202609090001_supabase_postgres.sql)
   once against a new, empty `enterprise_ai` schema. This transactional migration
   creates 51 enterprise/source tables and 5 runtime tables, foreign keys, indexes,
   and enables RLS. It contains schema only, not the packaged CSV records.
   It does not replace existing tables; it is not intended to be rerun.

   Keep `enterprise_ai` out of the Data API's exposed schemas. There are no browser
   RLS policies: `anon` and `authenticated` have no access. Use the migration owner's
   `postgres` connection for this backend; another DB role needs explicit grants
   and appropriate RLS access. The existing application accounts are separate from
   Supabase Auth.

4. Stop the backend while transferring existing runtime state, then import:

   ```powershell
   .\.venv\Scripts\python.exe backend/scripts/load_supabase.py --include-runtime
   ```

   Omit `--include-runtime` for fresh runtime state. `--runtime-path` can select a
   different SQLite file. The importer reads SQLite without modifying it and
   imports CSVs and runtime rows in one transaction. It refuses populated target
   tables and rolls back on failure, so a successful import must not be repeated.
   Use this importer for Supabase; the legacy `load_postgresql.py --replace`
   recreates tables and must not be used on the migrated schema.

5. Check the database from the project root before starting the backend:

   ```powershell
   .\.venv\Scripts\python.exe backend/scripts/check_database.py
   ```

   This read-only check tests the connection, required tables and row counts for
   users, employees, projects and tasks. Exit code 0 means ready, 1 means the
   connection/configuration/query failed, and 2 means tables or data are missing.
   It does not print credentials. If the hostname cannot be resolved, verify the
   exact URL in Supabase's Connect panel and try its Session pooler URI.

6. Start the backend with `.\run_backend.ps1` (or the dashboard with
   `.\run_dashboard.ps1`). `/api/health` should report
   `data_backend: supabase` and `runtime_backend: postgres`. Log in with an existing
   application account and check approvals, chat history and audit events.

No migration is applied to a remote project automatically. Automated tests force
CSV/SQLite storage and do not touch the database in `.env`.

For offline operation, set `DATA_BACKEND=csv` and `RUNTIME_BACKEND=auto` (SQLite).
For the legacy Docker PostgreSQL dataset loader, set `DATA_BACKEND=postgres` and
`RUNTIME_BACKEND=sqlite`. To move both stores to another PostgreSQL host, apply
the same SQL migration and use `RUNTIME_BACKEND=auto`.
