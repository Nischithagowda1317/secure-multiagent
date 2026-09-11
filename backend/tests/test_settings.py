import runpy
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
