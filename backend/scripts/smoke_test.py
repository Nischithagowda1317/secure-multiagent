from __future__ import annotations

import json
import sys

from fastapi.testclient import TestClient

from _bootstrap import PROJECT_ROOT  # noqa: F401
from app.main import app


def main() -> None:
    with TestClient(app) as client:
        health = client.get("/api/health")
        health.raise_for_status()
        accounts = client.get("/api/auth/demo-accounts")
        accounts.raise_for_status()
        account = next(
            (item for item in accounts.json() if "Project_Manager" in item["roles"]),
            accounts.json()[0],
        )
        login = client.post(
            "/api/auth/login",
            json={"email": account["email"], "password": account["temporary_password"]},
        )
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post(
            "/api/chat",
            data={"message": "Check Project Atlas status and identify overloaded team members."},
            headers=headers,
        )
        response.raise_for_status()
        body = response.json()
        checks = {
            "health": health.json(),
            "workflow_status": body.get("status"),
            "workflow_id": body.get("workflow_id"),
            "agent_count": len(body.get("agents", [])),
            "source_count": len(body.get("sources", [])),
            "confidence": body.get("confidence"),
        }
        print(json.dumps(checks, indent=2))
        if body.get("status") not in {"Completed", "Awaiting Approval"}:
            raise SystemExit("Smoke test did not complete successfully")


if __name__ == "__main__":
    main()
