import runpy
import errno
from pathlib import Path

import pytest


SETTINGS_FILE = Path(__file__).resolve().parents[1] / "app" / "settings.py"
NUMERIC_SETTINGS = {
    "JWT_EXP_MINUTES": ("jwt_exp_minutes", 480, "60", 60),
    "OPENAI_TIMEOUT_SECONDS": ("openai_timeout_seconds", 120.0, "30.5", 30.5),
    "MAX_UPLOAD_MB": ("max_upload_mb", 10, "5", 5),
    "ROUTER_CONFIDENCE_THRESHOLD": ("router_confidence_threshold", 0.6, "0", 0.0),
}


@pytest.fixture
def isolated_settings(monkeypatch, tmp_path):
    # Exercise module startup without loading credentials or writing live paths.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: None)
    for name in NUMERIC_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    for name in ("MODELS_ROOT", "RUNTIME_ROOT", "CHROMA_PATH"):
        monkeypatch.setenv(name, str(tmp_path / name.lower()))

    def load():
        return runpy.run_path(str(SETTINGS_FILE))["settings"]

    return load


@pytest.mark.parametrize("value", [None, "", " \t "])
def test_missing_or_blank_numeric_settings_use_defaults(
    monkeypatch, isolated_settings, value
):
    if value is not None:
        for name in NUMERIC_SETTINGS:
            monkeypatch.setenv(name, value)
    config = isolated_settings()
    for field, default, _, _ in NUMERIC_SETTINGS.values():
        assert getattr(config, field) == default


def test_explicit_numeric_settings_are_preserved(monkeypatch, isolated_settings):
    for name, (_, _, value, _) in NUMERIC_SETTINGS.items():
        monkeypatch.setenv(name, f" {value} ")
    config = isolated_settings()
    for field, _, _, expected in NUMERIC_SETTINGS.values():
        assert getattr(config, field) == expected


@pytest.mark.parametrize("name", NUMERIC_SETTINGS)
def test_invalid_nonempty_numeric_settings_still_fail(
    monkeypatch, isolated_settings, name
):
    monkeypatch.setenv(name, "invalid")
    with pytest.raises(ValueError):
        isolated_settings()


def test_vercel_import_with_read_only_bundle(monkeypatch, tmp_path):
    bundle = tmp_path / "task"
    app_dir = bundle / "app"
    app_dir.mkdir(parents=True)
    deployed_settings = app_dir / "settings.py"
    deployed_settings.write_text(SETTINGS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("RAG_BACKEND", "tfidf")
    for name in ("RUNTIME_ROOT", "MODELS_ROOT", "DATASET_ROOT"):
        monkeypatch.delenv(name, raising=False)
    # An unused Chroma setting must not cause a write in TF-IDF mode.
    monkeypatch.setenv("CHROMA_PATH", str(bundle / "chroma"))
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(scratch))

    def forbid_dotenv(*args, **kwargs):
        raise AssertionError("Vercel must use deployment environment variables")

    monkeypatch.setattr("dotenv.load_dotenv", forbid_dotenv)
    original_mkdir = Path.mkdir

    def read_only_bundle(path, *args, **kwargs):
        if not path.is_relative_to(scratch):
            raise OSError(errno.EROFS, "Read-only file system", str(path))
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", read_only_bundle)
    config = runpy.run_path(str(deployed_settings))["settings"]
    assert config.project_root == bundle
    assert config.models_root == bundle / "models"
    assert config.dataset_root == bundle / "datasets" / "Secure_Multi_Agent_Enterprise_Dataset"
    assert config.runtime_root == scratch / "enterprise-assistant"
    assert (config.runtime_root / "uploads").is_dir()
    assert not config.models_root.exists()
    assert not config.chroma_path.exists()


def test_local_paths_and_chroma_follow_runtime_override(monkeypatch, isolated_settings, tmp_path):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("CHROMA_PATH", raising=False)
    monkeypatch.setenv("RAG_BACKEND", "chroma")
    config = isolated_settings()
    assert config.project_root == SETTINGS_FILE.parents[2]
    assert config.runtime_root == tmp_path / "runtime_root"
    assert config.chroma_path == config.runtime_root / "chroma"
    assert config.chroma_path.is_dir()


def test_blank_snapshot_date_uses_dataset_default(monkeypatch, isolated_settings):
    monkeypatch.setenv("DATASET_SNAPSHOT_DATE", " ")
    assert isolated_settings().snapshot_date == "2026-08-28"
