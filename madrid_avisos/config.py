from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    streets: tuple[str, ...]
    problem: str
    description: str
    followup: str
    credentials: Path
    state: Path
    slack_token: str
    slack_channel: str


def _here(base: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else base / path


def load(path: Path) -> Config:
    try:
        raw = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    base = path.parent
    aviso = raw.get("aviso", {})
    slack = raw.get("slack", {})
    streets = tuple(str(s) for s in raw.get("streets", []))
    if not streets:
        raise ConfigError(f"{path}: `streets` is empty")
    if len({s.casefold() for s in streets}) != len(streets):
        raise ConfigError(f"{path}: `streets` has duplicates")
    description = str(aviso.get("description", "")).strip()
    if not description:
        raise ConfigError(f"{path}: `aviso.description` is required")
    return Config(
        streets=streets,
        problem=str(aviso.get("problem", "Suciedad")),
        description=description,
        followup=str(aviso.get("followup", "")).strip() or description,
        credentials=_here(base, str(raw.get("credentials", "credentials"))),
        state=_here(base, str(raw.get("state", "state.json"))),
        slack_token=str(slack.get("token", "")),
        slack_channel=str(slack.get("channel", "")),
    )


def read_credentials(path: Path) -> tuple[str, str]:
    try:
        lines = path.read_text().splitlines()
    except OSError as exc:
        raise ConfigError(f"credentials: {exc}") from exc
    pairs = dict(line.split("=", 1) for line in lines if "=" in line)
    email, password = pairs.get("email", "").strip(), pairs.get("password", "")
    if not email or not password:
        raise ConfigError(f"{path}: needs `email=` and `password=` lines")
    return email, password
