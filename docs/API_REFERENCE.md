# API Reference

The interactive OpenAPI page is available while the server runs:

```text
http://127.0.0.1:8000/docs
```

## Public endpoints

### `GET /api/health`

Returns application and configured backend status.

### `GET /api/config`

Returns supported files, snapshot date and configured backend names.

### `GET /api/auth/demo-accounts`

Returns local academic demo users.

### `POST /api/auth/login`

Request:

```json
{
  "email": "majid.aleusud@nexacore.example",
  "password": "Demo@123!"
}
```

Response contains a Bearer token and user profile.

## Authenticated endpoints

Send:

```text
Authorization: Bearer <access_token>
```

### `GET /api/auth/me`

Current user, roles and profile.

### `POST /api/chat`

Multipart form fields:

- `message`: text request;
- `files`: optional repeated upload field.

PowerShell example:

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/auth/login `
  -ContentType application/json `
  -Body '{"email":"majid.aleusud@nexacore.example","password":"Demo@123!"}'

$headers = @{ Authorization = "Bearer $($login.access_token)" }
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/chat `
  -Headers $headers `
  -Form @{ message = "Check Project Atlas status and identify overloaded team members." }
```

Main response fields:

- workflow ID/name and status;
- grounded answer;
- structured sections;
- security decision;
- agent traces;
- source references;
- confidence and grounding score;
- approval information;
- explanation and warnings.

### Dashboard

- `GET /api/dashboard/overview`
- `GET /api/dashboard/projects`
- `GET /api/dashboard/projects/{project_id}`
- `GET /api/dashboard/hr`
- `GET /api/dashboard/sales`
- `GET /api/dashboard/monitoring`

Each endpoint applies its required permission.

### Documents

- `GET /api/documents`
- `POST /api/documents/upload`
- `POST /api/documents/rebuild-index`

Persistent upload requires `document.upload`.

### Approvals

- `GET /api/approvals`
- `POST /api/approvals/{approval_id}/decision`

Decision body:

```json
{
  "decision": "Approve",
  "comment": "Evidence and workload were reviewed."
}
```

### Models

- `GET /api/models`
- `POST /api/models/reload`

### Audit

- `GET /api/audit`

## Error interpretation

- `400`: invalid file or request;
- `401`: missing/invalid login;
- `403`: valid login but insufficient permission;
- `404`: resource not found;
- `409`: approval state conflict;
- `500`: server or configuration failure.
