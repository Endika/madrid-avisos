"""Which aviso each street pushes, or whether it needs a new one."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .models import Aviso


@dataclass(frozen=True)
class CommentOn:
    aviso: Aviso
    closed: Aviso | None = None


@dataclass(frozen=True)
class OpenNew:
    closed: Aviso | None = None


Decision = CommentOn | OpenNew


def street_name(address: str) -> str:
    return address.split(",", 1)[0].strip().casefold()


def find(avisos: Sequence[Aviso], token: str) -> Aviso | None:
    return next((a for a in avisos if a.token == token), None)


def decide(
    street: str, tracked: Aviso | None, state: Mapping[str, str], avisos: Sequence[Aviso]
) -> Decision:
    """`tracked` is the aviso `state` holds for `street`, or None if the portal lost it."""
    if tracked and tracked.is_open:
        return CommentOn(tracked)
    taken = {t for other, t in state.items() if other != street}
    same_street = [
        a
        for a in avisos
        if a.is_open and a.token not in taken and street_name(a.address) == street_name(street)
    ]
    newest = max(same_street, key=lambda a: a.requested, default=None)
    return CommentOn(newest, closed=tracked) if newest else OpenNew(closed=tracked)
