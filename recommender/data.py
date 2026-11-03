"""Loading quiz data from URLs or local JSON files."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

# Original assignment endpoints. Override with environment variables (see .env.example).
# As of Nov 2026 only the jsonkeeper URL still resolves; api.jsonserve.com is offline.
DEFAULT_URLS = {
    "current_quiz": "https://www.jsonkeeper.com/b/LLQT",
    "submission": "https://api.jsonserve.com/rJvd7g",
    "history": "https://api.jsonserve.com/XgAgFJ",
}
ENV_VARS = {
    "current_quiz": "CURRENT_QUIZ_URL",
    "submission": "QUIZ_SUBMISSION_URL",
    "history": "HISTORICAL_QUIZ_URL",
}
FILE_NAMES = {
    "current_quiz": "current_quiz.json",
    "submission": "quiz_submission.json",
    "history": "historical_quiz.json",
}


def url_for(kind: str) -> str:
    return os.environ.get(ENV_VARS[kind], DEFAULT_URLS[kind])


def fetch_json(url: str, timeout: float = 20.0) -> Any:
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def load_all(data_dir: Path | None = None) -> dict[str, Any]:
    """Load the three inputs from ``data_dir`` if given, otherwise from the URLs.

    A missing input becomes ``None`` so the caller can degrade gracefully.
    """
    out: dict[str, Any] = {}
    for kind in FILE_NAMES:
        try:
            if data_dir is not None:
                path = Path(data_dir) / FILE_NAMES[kind]
                out[kind] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
            else:
                out[kind] = fetch_json(url_for(kind))
        except (requests.RequestException, ValueError, OSError) as exc:
            print(f"[warn] could not load {kind}: {exc}")
            out[kind] = None
    return out
