from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from ..domain.models import Aviso, Place


class Portal(Protocol):
    def login(self) -> None:
        pass

    def my_avisos(self) -> list[Aviso]:
        pass

    # Who files the aviso, in the portal's own shape; `create` gets it back untouched.
    def informant(self) -> Mapping[str, object]:
        pass

    # None when the portal no longer has that aviso.
    def lookup(self, token: str) -> Aviso | None:
        pass

    def locate(self, address: str) -> Place:
        pass

    def create(
        self, place: Place, *, problem: str, description: str, informant: Mapping[str, object]
    ) -> Aviso:
        pass

    def comment(self, aviso: Aviso, text: str) -> None:
        pass


class StateStore(Protocol):
    """Which aviso each street is pushing, kept from one run to the next."""

    def load(self) -> dict[str, str]:
        pass

    # Raises OSError when it cannot write; the run reports it instead of crashing.
    def save(self, state: Mapping[str, str]) -> None:
        pass
