# React Dashboard Development

## Two frontend forms are included

1. `frontend/dist` — immediately runnable static dashboard served by FastAPI.
2. `frontend/src` — React + TypeScript source for development and customization.

The prebuilt dashboard means Node.js is not required for the first demonstration.

## Development mode

Terminal 1:

```powershell
.\run_dashboard.ps1
```

Terminal 2:

```powershell
.\run_frontend_dev.ps1
```

Open:

```text
http://127.0.0.1:5173
```

Vite proxies `/api` requests to the FastAPI service.

## Production build

```powershell
cd frontend
npm install
npm run build
cd ..
```

Then restart FastAPI and open port 8000. FastAPI serves `frontend/dist/index.html` and its assets.

## Pages

- Login
- Overview
- Assistant
- Projects
- HR
- Sales
- Documents
- Approvals
- Monitoring
- Models
- Audit

## Safe UI extension rules

- Never hide a 403 denial and replace it with mock data.
- Do not place secrets in frontend source.
- Keep authorization enforcement in the backend.
- Render source, confidence, approval and warning information returned by the API.
- Do not show salaries or protected documents unless the API returns them for the current user.
