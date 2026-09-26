"""The boundaries the morning talks through. Adapters implement them; nothing here does I/O."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from ..domain import Aviso, Place


class Portal(Protocol):
    def login(self) -> None: ...
    def my_avisos(self) -> list[Aviso]: ...

    # Who files the aviso, in the portal's own shape; `create` gets it back untouched.
    def informant(self) -> Mapping[str, object]: ...

    # None when the portal no longer has that aviso.
    def lookup(self, token: str) -> Aviso | None: ...

    def locate(self, address: str) -> Place: ...
    def create(
        self, place: Place, *, problem: str, description: str, informant: Mapping[str, object]
    ) -> Aviso: ...
    def comment(self, aviso: Aviso, text: str) -> None: ...


class StateStore(Protocol):
    """Which aviso each street is pushing, kept from one morning to the next."""

    def load(self) -> dict[str, str]: ...

    # Raises OSError when it cannot write; the morning reports it instead of crashing.
    def save(self, state: Mapping[str, str]) -> None: ...
