"""The boundaries the morning talks through. Adapters implement them; nothing here does I/O."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from ..domain import Aviso, Place


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)

    def text(self) -> str:
        return self.body.decode("utf-8", "replace")


class Transport(Protocol):
    def request(
        self, method: str, url: str, *, headers: dict[str, str], body: bytes | None = None
    ) -> Response: ...


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


class Notifier(Protocol):
    def send(self, text: str) -> bool: ...
