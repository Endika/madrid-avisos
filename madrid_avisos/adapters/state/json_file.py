from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path


class JsonStateFile:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> dict[str, str]:
        try:
            raw = json.loads(self._path.read_text())
        except FileNotFoundError:
            return {}
        return {str(k): str(v) for k, v in raw.items()}

    def save(self, state: Mapping[str, str]) -> None:
        # Written aside and renamed, so a crash halfway never leaves a truncated file.
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(dict(state), indent=2, ensure_ascii=False) + "\n")
        tmp.replace(self._path)
