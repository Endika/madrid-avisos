from __future__ import annotations

import json
import os
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
        if not isinstance(raw, dict):
            raise ValueError(f"{self._path} is not a JSON object")
        return {str(k): str(v) for k, v in raw.items()}

    def save(self, state: Mapping[str, str]) -> None:
        # Written aside and renamed, so a crash halfway never leaves a truncated file.
        tmp = self._path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as out:
            out.write(json.dumps(dict(state), indent=2, ensure_ascii=False) + "\n")
            out.flush()
            os.fsync(out.fileno())
        tmp.replace(self._path)
