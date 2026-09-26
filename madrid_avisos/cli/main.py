from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ..adapters.http import UrllibTransport
from ..adapters.notify import Slack
from ..adapters.portal import PortalClient
from ..adapters.state import JsonStateFile
from ..application import Complaint, run_morning
from ..config import ConfigError, load, read_credentials
from ..ports import Transport

log = logging.getLogger("madrid_avisos")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="madrid-avisos")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true", help="log in and look, but send nothing")
    return parser


def main(argv: list[str] | None = None, transport: Transport | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    try:
        config = load(args.config)
        email, password = read_credentials(config.credentials)
    except ConfigError as exc:
        log.error("%s", exc)
        return 2

    http = transport or UrllibTransport()
    text, ok = run_morning(
        PortalClient(http, email, password),
        JsonStateFile(config.state),
        config.streets,
        Complaint(config.problem, config.description, config.followup),
        dry_run=args.dry_run,
    )
    print(text)
    if not args.dry_run and config.slack_token and config.slack_channel:
        ok = Slack(http, config.slack_token, config.slack_channel).send(text) and ok
    return 0 if ok else 1
