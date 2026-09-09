"""Package the included dashboard for Pages without backend dependencies."""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]


def build(output: Path, api_url: str) -> None:
    api_url = api_url.strip().rstrip("/")
    if api_url:
        parsed = urlsplit(api_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or not parsed.path.endswith("/api")
            or any(character.isspace() for character in api_url)
        ):
            raise ValueError(
                "BACKEND_API_URL must be an HTTPS URL ending in /api, "
                "without credentials, query parameters, or a fragment."
            )

    # Use a fresh output directory so unrelated files cannot enter the artifact.
    output.mkdir(parents=True, exist_ok=False)
    for filename in ("index.html", "styles.css", "app.js"):
        shutil.copyfile(ROOT / "frontend" / "dist" / filename, output / filename)
    (output / "config.js").write_text(
        "window.ENTERPRISE_CONFIG = "
        + json.dumps({"apiBaseUrl": api_url})
        + ";\n",
        encoding="utf-8",
    )
    (output / ".nojekyll").touch()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "pages-site")
    parser.add_argument("--api-url", default=os.getenv("BACKEND_API_URL", ""))
    args = parser.parse_args()
    try:
        build(args.output, args.api_url)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Pages build failed: {exc}\n")
    print(f"Pages dashboard prepared in {args.output}")
    if not args.api_url.strip():
        print("No backend URL configured; the site will display the service setup screen.")
