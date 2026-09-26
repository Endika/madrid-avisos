from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Aviso:
    token: str
    number: str
    address: str
    status_type: str
    status_name: str
    # ISO 8601 as the portal sends it, so newer sorts after older as plain text.
    requested: str

    @property
    def is_open(self) -> bool:
        return not self.status_type.startswith("final")


@dataclass(frozen=True)
class Place:
    address: str
    lat: float
    lng: float
    # The geocoder's answers about the spot (street type, postcode…), sent back on create.
    data: tuple[tuple[str, Any], ...]
