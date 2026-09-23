# Vercel deployment

Deploy the repository root, using the services in `vercel.json`. Vercel loads
`app.main:app` automatically; do not use `run_dashboard.ps1` or a long-running
Uvicorn command as the Build Command. The backend build command copies the
existing models and dataset into its service bundle. It does not train models
or import data into Supabase.

In Vercel's project Environment Variables, configure Production (and Preview
if needed):

```dotenv
DATA_BACKEND=supabase
DATABASE_URL=<your Supabase Session pooler PostgreSQL URL>
DATABASE_SCHEMA=enterprise_ai
RUNTIME_BACKEND=postgres
JWT_SECRET=<your generated secret>
RAG_BACKEND=tfidf
LLM_PROVIDER=openai
OPENAI_API_KEY=<your API key>
```

Use `LLM_PROVIDER=extractive` to run without an external language model.
The local `.env` is not loaded on Vercel. Supabase must already have the migration
and imported data described in [SUPABASE.md](SUPABASE.md).

Remove custom `MODELS_ROOT`, `DATASET_ROOT`, `RUNTIME_ROOT`, and `CHROMA_PATH`
overrides unless you intentionally need them. Defaults read the bundled assets
and write temporary runtime files under `/tmp/enterprise-assistant` on Vercel.
Do not set `MODELS_ROOT` to `/tmp`: that would hide the bundled trained models.

Commit and push the changes to the connected Git branch, then deploy that new
commit. Environment variable changes also require a new deployment. Check
`/api/auth/demo-accounts`, then sign in using an existing application account.
There is no need to rerun the database migration for this deployment fix.

The error `Read-only file system: '/var/models'` came from assuming the original
repository layout after Vercel flattened the backend service, and creating model
directories at import time. Startup now only creates writable runtime folders.

Runtime files in `/tmp` are temporary and are not shared across instances.
Supabase persists chats, approvals and audit data, but this application still
stores uploaded files and rebuilt runtime RAG indexes on disk. Durable uploads
require shared object storage and a persistent index; this fix does not add them.

References: [Vercel Services](https://vercel.com/docs/services),
[Vercel runtimes](https://vercel.com/docs/functions/runtimes).
