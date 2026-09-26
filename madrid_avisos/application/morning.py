"""One morning: every street gets pushed once, by commenting on its aviso or opening one."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..domain import Aviso, policy
from ..ports import Portal, StateStore
from .outcomes import Action, Outcome
from .summary import aborted, summary, unsaved

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Complaint:
    problem: str
    description: str
    followup: str


def run_morning(
    portal: Portal,
    store: StateStore,
    streets: Sequence[str],
    complaint: Complaint,
    *,
    dry_run: bool,
) -> tuple[str, bool]:
    """The summary to report, and whether nothing failed along the way."""
    try:
        state = store.load()
        portal.login()
        outcomes = push_streets(portal, streets, complaint, state, dry_run=dry_run)
    except Exception as exc:
        log.exception("run aborted")
        return aborted(str(exc) or type(exc).__name__), False
    text = summary(outcomes, dry_run=dry_run)
    ok = all(o.action is not Action.FAILED for o in outcomes)
    if not dry_run:
        try:
            store.save(state)
        except OSError as exc:
            log.error("could not save state: %s", exc)
            return text + unsaved(str(exc)), False
    return text, ok


def push_streets(
    portal: Portal,
    streets: Sequence[str],
    complaint: Complaint,
    state: dict[str, str],
    *,
    dry_run: bool,
) -> list[Outcome]:
    avisos = portal.my_avisos()
    informant = portal.informant()
    outcomes = []
    for street in streets:
        try:
            decision = _decide(portal, street, state, avisos)
            outcome = _carry_out(portal, street, decision, complaint, informant, dry_run=dry_run)
        except Exception as exc:
            log.exception("%s failed", street)
            outcome = Outcome(street, Action.FAILED, error=str(exc) or type(exc).__name__)
        # Updated as we go: the next street must not adopt the aviso this one just took.
        if outcome.aviso:
            state[street] = outcome.aviso.token
        outcomes.append(outcome)
    return outcomes


def _decide(
    portal: Portal, street: str, state: Mapping[str, str], avisos: Sequence[Aviso]
) -> policy.Decision:
    token = policy.unlisted(street, state, avisos)
    looked_up = portal.lookup(token) if token else None
    return policy.decide(street, state, avisos, looked_up)


def _carry_out(
    portal: Portal,
    street: str,
    decision: policy.Decision,
    complaint: Complaint,
    informant: Mapping[str, object],
    *,
    dry_run: bool,
) -> Outcome:
    if isinstance(decision, policy.CommentOn):
        # The portal refuses to let the informant reiterate (403), so a comment it is.
        if not dry_run:
            portal.comment(decision.aviso, complaint.followup)
        return Outcome(street, Action.COMMENTED, decision.aviso, decision.closed, simulated=dry_run)
    place = portal.locate(street)
    if dry_run:
        return Outcome(street, Action.CREATED, simulated=True)
    aviso = portal.create(
        place,
        problem=complaint.problem,
        description=complaint.description,
        informant=informant,
    )
    return Outcome(street, Action.CREATED, aviso, decision.closed)
