# madrid-avisos

Every morning, pushes the street-cleaning avisos of your streets on
[avisos.madrid.es](https://avisos.madrid.es/), and tells you on Slack what it did.

For each street in the config:

- **Its aviso is open** → it reiterates it. Once reiterated (or if the portal refuses to
  reiterate your own aviso), it adds a comment instead.
- **It has none, or the last one was closed** → it opens a new one, and the summary says how
  the old one was closed.

It only uses the standard library, so it runs on a stock `python3` ≥ 3.11 (a Raspberry Pi).

## Setup

```sh
mkdir -p ~/.config/madrid-avisos && chmod 700 ~/.config/madrid-avisos
cp config.example.toml ~/.config/madrid-avisos/config.toml   # then edit it
read -rp 'Email: ' E; read -rsp 'Password: ' P; echo
umask 077; printf 'email=%s\npassword=%s\n' "$E" "$P" > ~/.config/madrid-avisos/credentials; unset E P
```

Addresses must be written exactly as the portal's geocoder returns them
(`Calle de Toledo, 29`). An address it cannot pin to a single point is reported as an
error, never guessed.

## Run

```sh
python3 -m madrid_avisos --config ~/.config/madrid-avisos/config.toml --dry-run  # looks, sends nothing
python3 -m madrid_avisos --config ~/.config/madrid-avisos/config.toml
```

Cron, every day at 05:30:

```cron
30 5 * * * cd ~/madrid-avisos && flock -n /tmp/madrid-avisos.lock /usr/bin/python3 -m madrid_avisos --config ~/.config/madrid-avisos/config.toml >> ~/madrid-avisos/avisos.log 2>&1
```

## Development

```sh
make install
make check   # ruff, format, mypy --strict, pytest
```
