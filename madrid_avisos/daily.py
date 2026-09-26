"""One morning: every street gets pushed once, by commenting on its aviso or opening one."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .domain import Aviso, policy
from .ports import Portal

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Outcome:
    street: str
    action: str  # created, commented, failed
    aviso: Aviso | None = None
    note: str = ""


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


def _decide(
    portal: Portal, street: str, state: dict[str, str], avisos: list[Aviso]
) -> policy.Decision:
    token = policy.unlisted(street, state, avisos)
    looked_up = portal.lookup(token) if token else None
    return policy.decide(street, state, avisos, looked_up)


def run(portal: Portal, config: Config, state: dict[str, str], *, dry_run: bool) -> list[Outcome]:
    avisos = portal.my_avisos()
    informant = portal.informant()
    outcomes: list[Outcome] = []
    for street in config.streets:
        try:
            decision = _decide(portal, street, state, avisos)
            target = decision.aviso if isinstance(decision, policy.CommentOn) else None
            closed = decision.closed
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
                # The portal refuses to let the informant reiterate (403), so a comment it is.
                if not dry_run:
                    portal.comment(target, config.followup)
                action, extra = "commented", "simulado" if dry_run else ""
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
