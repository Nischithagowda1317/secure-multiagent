"""Copy read-only inference assets into the backend service at build time."""
from pathlib import Path
import shutil


def prepare_assets(project_root: Path, backend_root: Path) -> None:
    # Copy only packaged assets, never .env, runtime databases, or uploads.
    for name in ("models", "datasets"):
        source = project_root / name
        if not source.is_dir():
            raise FileNotFoundError(f"Required deployment assets are missing: {source}")
        shutil.copytree(
            source,
            backend_root / name,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        print(f"Bundled {name} for the backend service.")


if __name__ == "__main__":
    backend_root = Path(__file__).resolve().parents[1]
    prepare_assets(backend_root.parent, backend_root)
