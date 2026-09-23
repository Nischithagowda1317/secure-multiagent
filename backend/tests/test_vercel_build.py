import runpy
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


BUILD_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "prepare_vercel.py"


def test_bundle_copies_assets_without_local_secrets_or_state(tmp_path):
    repo = tmp_path / "repo"
    backend = repo / "backend"
    backend.mkdir(parents=True)
    for name in ("models", "datasets"):
        (repo / name).mkdir()
        (repo / name / "asset.bin").write_bytes(b"inference asset")
    (repo / ".env").write_text("SECRET=not-for-deployment")
    (repo / "runtime").mkdir()
    (repo / "runtime" / "private.db").write_bytes(b"private")
    prepare = runpy.run_path(str(BUILD_SCRIPT))["prepare_assets"]
    prepare(repo, backend)
    prepare(repo, backend)  # Cached builds may already have the directories.
    for name in ("models", "datasets"):
        assert (backend / name / "asset.bin").read_bytes() == b"inference asset"
    assert not (backend / ".env").exists()
    assert not (backend / "runtime").exists()


def test_bundle_fails_when_required_assets_are_missing(tmp_path):
    prepare = runpy.run_path(str(BUILD_SCRIPT))["prepare_assets"]
    with pytest.raises(FileNotFoundError, match="Required deployment assets"):
        prepare(tmp_path, tmp_path / "backend")


def test_flattened_bundle_can_start_and_login_with_read_only_assets(tmp_path):
    project = BUILD_SCRIPT.parents[2]
    bundle = tmp_path / "task"
    shutil.copytree(project / "backend" / "app", bundle / "app")
    runpy.run_path(str(BUILD_SCRIPT))["prepare_assets"](project, bundle)
    scratch = tmp_path / "runtime"
    env = os.environ.copy()
    for name in ("MODELS_ROOT", "DATASET_ROOT", "CHROMA_PATH", "FRONTEND_DIST"):
        env.pop(name, None)
    env.update({
        "VERCEL": "1",
        "PYTHONPATH": str(bundle),
        "PYTHONDONTWRITEBYTECODE": "1",
        "RUNTIME_ROOT": str(scratch),
        "DATA_BACKEND": "csv",
        "RUNTIME_BACKEND": "sqlite",
        "RAG_BACKEND": "tfidf",
        "LLM_PROVIDER": "extractive",
        "OPENAI_API_KEY": "",
    })
    script = '''
import errno
import os
from pathlib import Path
from fastapi.testclient import TestClient

original_mkdir = Path.mkdir
def readonly_mkdir(path, *args, **kwargs):
    if not path.is_relative_to(Path(os.environ["RUNTIME_ROOT"])):
        raise OSError(errno.EROFS, "Read-only file system", str(path))
    return original_mkdir(path, *args, **kwargs)
Path.mkdir = readonly_mkdir

from app.main import app
with TestClient(app) as client:
    response = client.get("/api/auth/demo-accounts")
    assert response.status_code == 200, response.text
    assert response.json()
    login = client.post("/api/auth/login", json={
        "email": "abd.alruhmin.alnasar@nexacore.example", "password": "Demo@123!"
    })
    assert login.status_code == 200, login.text
    headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.get("/api/auth/me", headers=headers).status_code == 200
    assert app.state.services.rag._base is not None
print("Bundled startup, model loading and login succeeded.")
'''
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=bundle, env=env,
        text=True, capture_output=True, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
