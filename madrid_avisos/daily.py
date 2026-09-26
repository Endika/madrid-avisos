"""One morning: every street gets pushed once, by reiterating, commenting or opening an aviso."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .config import Config
from .portal import Aviso, Place, PortalError

log = logging.getLogger(__name__)


class Portal(Protocol):
    def profile(self) -> dict[str, object]: ...
    def my_avisos(self) -> list[Aviso]: ...
    def aviso(self, token: str) -> Aviso: ...
    def locate(self, address: str) -> Place: ...
    def create(
        self, place: Place, *, problem: str, description: str, informant: dict[str, object]
    ) -> Aviso: ...
    def reiterate(self, aviso: Aviso, description: str) -> None: ...
    def comment(self, aviso: Aviso, description: str) -> None: ...


@dataclass(frozen=True)
class Outcome:
    street: str
    action: str  # created, reiterated, commented, failed
    aviso: Aviso | None = None
    note: str = ""


def _street_name(address: str) -> str:
    return address.split(",", 1)[0].strip().casefold()


def load_state(path: Path) -> dict[str, str]:
    try:
        raw = json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def save_state(path: Path, state: dict[str, str]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)


def _pick(
    portal: Portal, street: str, known: str | None, avisos: list[Aviso], taken: set[str]
) -> tuple[Aviso | None, Aviso | None]:
    """(open aviso to push, the tracked one if it has closed since)."""
    tracked = next((a for a in avisos if a.token == known), None) if known else None
    if known and tracked is None:
        try:
            tracked = portal.aviso(known)
        except PortalError as exc:
            if exc.status != 404:
                raise
    if tracked and tracked.is_open:
        return tracked, None
    # Nothing tracked yet, or it closed: adopt my newest open aviso on the same street, if any.
    same_street = [
        a
        for a in avisos
        if a.is_open and a.token not in taken and _street_name(a.address) == _street_name(street)
    ]
    same_street.sort(key=lambda a: a.requested, reverse=True)
    return (same_street[0] if same_street else None), tracked


def _push(portal: Portal, aviso: Aviso, text: str, dry_run: bool) -> tuple[str, str]:
    if dry_run:
        return ("commented" if aviso.supporting else "reiterated"), "simulado"
    if not aviso.supporting:
        try:
            portal.reiterate(aviso, text)
            return "reiterated", ""
        except PortalError as exc:
            # Only a real refusal (4xx) earns the fallback; a network blip or a 5xx is a failure.
            if not 400 <= exc.status < 500 or exc.status == 429:
                raise
            log.info("reiteration refused for %s (%s); commenting instead", aviso.number, exc)
            portal.comment(aviso, text)
            return "commented", f"reiterar rechazado: {exc}"
    portal.comment(aviso, text)
    return "commented", ""


def run(portal: Portal, config: Config, state: dict[str, str], *, dry_run: bool) -> list[Outcome]:
    avisos = portal.my_avisos()
    informant = portal.profile()
    outcomes: list[Outcome] = []
    for street in config.streets:
        taken = {token for other, token in state.items() if other != street}
        try:
            target, closed = _pick(portal, street, state.get(street), avisos, taken)
            note = f"el anterior #{closed.number} se cerró: {closed.status_name}" if closed else ""
            if target is None:
                if dry_run:
                    portal.locate(street)
                    outcomes.append(Outcome(street, "created", None, "simulado"))
                    continue
                target = portal.create(
                    portal.locate(street),
                    problem=config.problem,
                    description=config.description,
                    informant=informant,
                )
                action, extra = "created", ""
            else:
                action, extra = _push(portal, target, config.followup, dry_run)
            state[street] = target.token
            outcomes.append(
                Outcome(street, action, target, "; ".join(n for n in (note, extra) if n))
            )
        except Exception as exc:
            log.exception("%s failed", street)
            outcomes.append(Outcome(street, "failed", None, str(exc) or type(exc).__name__))
    return outcomes


VERBS = {
    "created": "aviso nuevo",
    "reiterated": "reiterado",
    "commented": "comentado",
    "failed": "ERROR",
}


def summary(outcomes: list[Outcome], *, dry_run: bool) -> str:
    head = "Avisos de limpieza" + (" (simulado, no se ha enviado nada)" if dry_run else "")
    lines = [head]
    for o in outcomes:
        line = f"• {o.street}: {VERBS[o.action]}"
        if o.aviso:
            line += f" #{o.aviso.number}"
            if o.aviso.status_name:
                line += f" ({o.aviso.status_name})"
        if o.note:
            line += f", {o.note}"
        lines.append(line)
    return "\n".join(lines)
