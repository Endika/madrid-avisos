"""Every word the user reads, in Spanish like the portal itself."""

from __future__ import annotations

from collections.abc import Iterable

from .outcomes import Action, Outcome

VERBS = {
    Action.CREATED: "aviso nuevo",
    Action.COMMENTED: "comentado",
    Action.FAILED: "ERROR",
}


def summary(outcomes: Iterable[Outcome], *, dry_run: bool) -> str:
    head = "Avisos de limpieza" + (" (simulado, no se ha enviado nada)" if dry_run else "")
    return "\n".join([head, *(_line(o) for o in outcomes)])


def aborted(reason: str) -> str:
    return f"Avisos de limpieza: no se ha podido empezar. {reason}"


def unsaved(reason: str) -> str:
    return f"\nERROR: no se ha podido guardar el estado ({reason}); mañana puede duplicar."


def _line(o: Outcome) -> str:
    line = f"• {o.street}: {VERBS[o.action]}"
    if o.aviso:
        line += f" #{o.aviso.number}"
        if o.aviso.status_name:
            line += f" ({o.aviso.status_name})"
    if notes := _notes(o):
        line += ", " + "; ".join(notes)
    return line


def _notes(o: Outcome) -> list[str]:
    notes = []
    if o.closed:
        notes.append(f"el anterior #{o.closed.number} se cerró: {o.closed.status_name}")
    if o.simulated:
        notes.append("simulado")
    if o.error:
        notes.append(o.error)
    return notes
