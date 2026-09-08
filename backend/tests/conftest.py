from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault(
    "JWT_SECRET", "pytest-secret-key-that-is-safely-longer-than-thirty-two-bytes"
)
os.environ.setdefault("LLM_PROVIDER", "extractive")
TEST_RUNTIME_ROOT = PROJECT_ROOT / "runtime" / "pytest"
os.environ["RUNTIME_ROOT"] = str(TEST_RUNTIME_ROOT)

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    # Keep test mutations separated from an existing live demonstration database.
    runtime = TEST_RUNTIME_ROOT
    runtime.mkdir(parents=True, exist_ok=True)
    for name in ("assistant_runtime.db", "assistant_runtime.db-shm", "assistant_runtime.db-wal"):
        (runtime / name).unlink(missing_ok=True)
    with TestClient(app) as test_client:
        yield test_client


def login_headers(client: TestClient, email: str, password: str = "Demo@123!") -> dict[str, str]:
    response = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
