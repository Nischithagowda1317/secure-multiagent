from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from _bootstrap import PROJECT_ROOT


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    models_root = PROJECT_ROOT / "models"
    artifacts = []
    for path in sorted(models_root.glob("**/*")):
        if not path.is_file() or path.name == "model_manifest.json":
            continue
        if path.suffix.lower() not in {".joblib", ".pt", ".json"}:
            continue
        artifacts.append(
            {
                "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }
    output = models_root / "model_manifest.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[OK] Model manifest written to {output}")


if __name__ == "__main__":
    main()
