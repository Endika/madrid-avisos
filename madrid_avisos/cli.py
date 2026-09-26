from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import daily, slack
from .config import ConfigError, load, read_credentials
from .http import Transport, UrllibTransport
from .portal import Portal

log = logging.getLogger("madrid_avisos")


def main(argv: list[str] | None = None, transport: Transport | None = None) -> int:
    parser = argparse.ArgumentParser(prog="madrid-avisos")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true", help="log in and look, but send nothing")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    try:
        config = load(args.config)
        email, password = read_credentials(config.credentials)
    except ConfigError as exc:
        log.error("%s", exc)
        return 2

    http = transport or UrllibTransport()
    portal = Portal(http)
    try:
        state = daily.load_state(config.state)
        portal.login(email, password)
        outcomes = daily.run(portal, config, state, dry_run=args.dry_run)
    except Exception as exc:
        log.exception("run aborted")
        text = f"Avisos de limpieza: no se ha podido empezar. {exc or type(exc).__name__}"
        ok = False
    else:
        text = daily.summary(outcomes, dry_run=args.dry_run)
        ok = all(o.action != "failed" for o in outcomes)
        if not args.dry_run:
            try:
                daily.save_state(config.state, state)
            except OSError as exc:
                log.error("could not save state: %s", exc)
                text += (
                    f"\nERROR: no se ha podido guardar el estado ({exc}); mañana puede duplicar."
                )
                ok = False

    print(text)
    if not args.dry_run and config.slack_token and config.slack_channel:
        ok = slack.send(http, config.slack_token, config.slack_channel, text) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
