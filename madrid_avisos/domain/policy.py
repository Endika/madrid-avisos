"""Which aviso each street pushes this morning, or whether it needs a new one."""

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


def unlisted(street: str, state: Mapping[str, str], avisos: Sequence[Aviso]) -> str | None:
    """The street's tracked token when the list of my avisos no longer shows it."""
    token = state.get(street)
    if token and all(a.token != token for a in avisos):
        return token
    return None


def decide(
    street: str,
    state: Mapping[str, str],
    avisos: Sequence[Aviso],
    looked_up: Aviso | None = None,
) -> Decision:
    """`looked_up` is what the portal said about the `unlisted` token, if it still has it."""
    token = state.get(street)
    tracked = next((a for a in avisos if a.token == token), looked_up) if token else None
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
