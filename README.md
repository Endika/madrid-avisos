# madrid-avisos

Keeps your street-cleaning avisos on [avisos.madrid.es](https://avisos.madrid.es/) alive.
Every morning, for each street you list, it adds a comment to your open aviso, or opens a new
one if the last was closed, and tells you on Slack what it did and how each aviso stands.

It's built to run from cron on a Raspberry Pi. It uses only the standard library, so a stock
`python3` 3.11 or newer is enough.

It isn't an official client. It talks to the portal's API the same way the web app does, with
your own account.

## What the API won't tell you

- **You can't reiterate your own aviso.** `POST /request/{token}/reiteration` answers
  `403 … is the informant`. Reiterating is for backing somebody else's aviso, so the daily
  push is a comment.
- **Login is a plain form with no captcha.** It answers `302` with the token in the
  `Location` query string (`?token=…&expires_in=2592000`), so every run just logs in again.
- **Addresses go through the portal's own geocoder**
  (`/location-additional-data?formatted_address=…`). An address it can't pin to exactly one
  point is reported as an error and never guessed. Write it the way the portal does:
  `Calle Mayor, 1`.
- **The problem question is mandatory.** A street-cleaning aviso needs an answer to
  "¿Cuál es el problema?" (`Suciedad`, `Excrementos`, `Manchas u olores`…).

## What a morning does

For each street:

1. **Its aviso is still open**: it adds a comment to it.
2. **It has none yet**: it adopts your newest open aviso on the same street, if you already
   filed one by hand. If you haven't, it opens one.
3. **Its aviso was closed**: it opens a new one, and the summary says how the old one closed.

Two addresses never share one aviso. When something fails (login, network, a page that isn't
JSON), that street shows as `ERROR` in the summary and the rest carry on. Nothing fails
silently.

## Getting started

You need Python 3.11 or newer and an account on avisos.madrid.es (the "cuenta Madrid"
email-and-password login).

```sh
git clone https://github.com/Endika/madrid-avisos && cd madrid-avisos
mkdir -p ~/.config/madrid-avisos && chmod 700 ~/.config/madrid-avisos
cp config.example.toml ~/.config/madrid-avisos/config.toml   # then edit it
```

Store your credentials without them showing on screen or ending up in your shell history:

```sh
read -rp 'Email: ' E; read -rsp 'Password: ' P; echo
umask 077; printf 'email=%s\npassword=%s\n' "$E" "$P" > ~/.config/madrid-avisos/credentials; unset E P
```

Look before you send anything:

```sh
python3 -m madrid_avisos --config ~/.config/madrid-avisos/config.toml --dry-run
```

This logs in, reads your avisos and geocodes your streets. It posts nothing and writes no
state. When the plan looks right, drop `--dry-run`.

## Cron

Every day at 05:30:

```cron
30 5 * * * cd ~/madrid-avisos && flock -n /tmp/madrid-avisos.lock /usr/bin/python3 -m madrid_avisos --config ~/.config/madrid-avisos/config.toml >> ~/madrid-avisos/avisos.log 2>&1
```

The Slack summary needs a bot token with `chat:write` and the ID of a channel the bot has
joined. Leave `[slack]` out and the summary only goes to stdout.

## Use it for what it's for

This tool is for a street that stays dirty until somebody files an aviso. It acts on your own
avisos only: one comment a day, and a new aviso only when the city has closed the last one.
Please don't point it at streets you don't know, and don't run it more than once a day.

## Development

```sh
make install
make check   # ruff, format, mypy --strict, pytest
```

The tests run the real client against an in-memory version of the portal and Slack. There
are no mocks and no network.

## Layout

Ports and adapters, with the decision kept away from the plumbing:

```
domain/       Aviso, Place and the policy: which aviso each street pushes, or a new one
ports/        Portal, Notifier, StateStore and the HTTP Transport
adapters/     portal/ (the avisos.madrid.es API), notify/ (Slack), state/ (JSON), http.py
application/  the morning itself, and every word of the summary
cli/          argparse and the composition root
```

The domain does no I/O, so the rules (never two streets on one aviso, adopt your newest open
one on the same street) are tested on their own, with plain values.

## License

[MIT](LICENSE)
