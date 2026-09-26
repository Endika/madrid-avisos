from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..domain import Aviso


class Action(Enum):
    CREATED = "created"
    COMMENTED = "commented"
    FAILED = "failed"


@dataclass(frozen=True)
class Outcome:
    street: str
    action: Action
    aviso: Aviso | None = None
    closed: Aviso | None = None
    simulated: bool = False
    error: str = ""
