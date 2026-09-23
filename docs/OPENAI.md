# OpenAI API setup

Set these values in the backend `.env` at the project root:

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4.1-mini
OPENAI_TIMEOUT_SECONDS=120
LLM_FALLBACK_PROVIDER=extractive
```

Restart the backend with `.\run_dashboard.ps1`. The key stays on the backend;
do not add it to frontend configuration or a `VITE_` variable. Existing `httpx`
dependencies handle the API requests; no local model download is needed.

The provider calls the [OpenAI Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create)
with authorization-filtered evidence, the user's question and structured agent
results. That content is sent to OpenAI for generation. Requests set `store=false`
to disable response storage; this does not override other account data-retention
policies. Source citations, numeric validation, RBAC and approval decisions remain
under backend control.

`OPENAI_MODEL` is configurable; the default is
[`gpt-4.1-mini`](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
Use a Responses-compatible model available to your API project.

`/api/health` reports `llm_provider`, `llm_model`, `llm_available` and
`fallback_provider`. Its OpenAI check verifies model access without generating
text; it does not guarantee generation quota. Missing keys, timeouts, API errors,
incomplete answers and rejected numeric claims use the extractive fallback.
For fully offline answers set `LLM_PROVIDER=extractive`.

Tests use mock API responses and do not make live OpenAI requests.

## Troubleshooting fallback warnings

`LLM provider failed; using fallback provider` means the workflow continued
with an extractive answer after generation failed. For HTTP failures, logs now
include the status and the API's `error.code` and `error.type` when available,
without logging the response message, request body, or authorization header:

```text
HTTPStatusError: HTTP 429 code=insufficient_quota type=insufficient_quota
```

Check the actual code before changing configuration:

- `401`: verify the active API key and project access.
- `429`: distinguish rate limiting from exhausted credits or spending limits.
  Billing and quota failures require fixing the applicable credits or limits;
  retrying alone will not resolve them.
- `400` or `404`: check request parameters and access to the configured model.
- `500` or `503`: the provider may be temporarily unavailable; retry later.

On Vercel, configure `OPENAI_API_KEY`, `LLM_PROVIDER=openai` and
`OPENAI_MODEL=gpt-4.1-mini` in the deployment's environment variables and
redeploy. Updating your computer's `.env` does not update Vercel. For local
changes, restart the backend.

See [OpenAI error codes](https://developers.openai.com/api/docs/guides/error-codes).
