# Optional PostgreSQL and ChromaDB Setup

For hosted PostgreSQL with enterprise and runtime data in Supabase, follow
[Supabase setup and migration](SUPABASE.md).

The supplied default is deliberately easy to run:

```text
CSV read layer + SQLite runtime state + TF-IDF RAG
```

This already demonstrates all required concepts. The optional integrations below provide a production-style extension.

## PostgreSQL using Docker Desktop

### 1. Complete normal setup

```powershell
.\setup_and_train.ps1
```

### 2. Start and load PostgreSQL

```powershell
.\setup_postgresql.ps1 -Replace
```

This command:

- starts PostgreSQL 16 using `docker-compose.yml`;
- installs SQLAlchemy and psycopg;
- creates schema `enterprise_ai`;
- loads every curated CSV and the agent-performance source;
- creates useful indexes.

### 3. Edit `.env`

Change:

```text
DATA_BACKEND=csv
```

to:

```text
DATA_BACKEND=postgres
RUNTIME_BACKEND=sqlite
```

Keep:

```text
DATABASE_URL=postgresql+psycopg://enterprise_user:enterprise_password@127.0.0.1:5432/enterprise_assistant
DATABASE_SCHEMA=enterprise_ai
```

### 4. Restart

```powershell
.\run_dashboard.ps1
```

Check `/api/health`; it should report `data_backend` as `postgres`.

### Return to CSV mode

Set:

```text
DATA_BACKEND=csv
```

and restart.

## ChromaDB

### 1. Build the collection

```powershell
.\setup_chroma.ps1 -Force
```

This installs ChromaDB and creates:

```text
runtime\chroma
```

The collection stores:

- chunk text;
- document/section metadata;
- classification;
- allowed roles;
- required permission;
- deterministic 4096-dimensional local embeddings.

### 2. Edit `.env`

Change:

```text
RAG_BACKEND=tfidf
```

to:

```text
RAG_BACKEND=chroma
```

### 3. Restart the dashboard

```powershell
.\run_dashboard.ps1
```

If ChromaDB is missing or the collection cannot be opened, the code safely falls back to the stored TF-IDF base index rather than making the whole dashboard unusable.

## OpenAI API answers

Follow [OpenAI API setup](OPENAI.md) to configure `OPENAI_API_KEY` and `OPENAI_MODEL`. Authorized evidence is sent to OpenAI; API failures use the extractive fallback.
