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
OPENAI_API_KEY=<your OpenAI API key>
OPENAI_MODEL=gpt-4.1-mini
OPENAI_TIMEOUT_SECONDS=120
LLM_FALLBACK_PROVIDER=none
```

Generated answers use the OpenAI Responses API. Keep `LLM_FALLBACK_PROVIDER=none`
to show a clear error if generation fails instead of returning an offline answer.
Set the key on the backend only, following the [OpenAI quickstart](https://developers.openai.com/api/docs/quickstart).
No local language model is needed. Remove any old `NVIDIA_*` deployment variables.

`OPENAI_MODEL` must be the literal model name `gpt-4.1-mini`. Put the OpenAI key
only in `OPENAI_API_KEY`. A key pasted into the model field causes the availability
probe and generation to fail. The provider rejects recognized key values in that
field without exposing them in health responses, metrics, or model request URLs.
Also replace an existing `LLM_FALLBACK_PROVIDER=extractive` override with `none`
when OpenAI-only answers are required.

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

## Assistant turns blank after a response

`Cannot read properties of null (reading 'toFixed')` is a frontend rendering
error. Structured evidence sources can legitimately have `score: null`.
`EvidenceSources.tsx` handles that by only formatting finite numbers. The old
production bundle `index-D2PdnPG7.js` checked only for `undefined` and still
crashes on `null`.

Deploy the latest source commit containing `EvidenceSources.tsx`; redeploying
an older commit will reproduce the bug. The frontend service runs its regression
tests and builds fresh Vite assets. If manually redeploying, disable the existing
build cache, then confirm that the successful deployment is assigned to the
production domain. Reload with Ctrl+Shift+R and sign in again if `/api/auth/me`
returns 401. That 401 is an application session failure, not an OpenAI API error.

If production now serves a different asset filename while an existing browser
tab still reports `index-D2PdnPG7.js`, close that tab and open a new private window.
In Chrome DevTools you can also select Network > Disable cache and reload. An
already-open page keeps executing its previously loaded JavaScript after a deployment.

After deployment, `/api/health` should report the intended `llm_provider` and
`llm_model`. Its availability probe checks the model catalog; submit an assistant
question to confirm generation and inspect the response's LLM validation or
server logs for fallback usage. Test a Project Atlas question too, since its
structured sources include null similarity scores.

The error `Read-only file system: '/var/models'` came from assuming the original
repository layout after Vercel flattened the backend service, and creating model
directories at import time. Startup now only creates writable runtime folders.

Runtime files in `/tmp` are temporary and are not shared across instances.
Supabase persists chats, approvals and audit data, but this application still
stores uploaded files and rebuilt runtime RAG indexes on disk. Durable uploads
require shared object storage and a persistent index; this fix does not add them.

References: [Vercel Services](https://vercel.com/docs/services),
[Vercel runtimes](https://vercel.com/docs/functions/runtimes).
