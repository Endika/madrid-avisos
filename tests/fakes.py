"""avisos.madrid.es and Slack in memory, behind the same `Transport` the real client uses."""

from __future__ import annotations

import json
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Any

from madrid_avisos.http import Response
from madrid_avisos.portal import API, LOGIN

TOKEN = "jwt-abc"


@dataclass
class FakeMadrid:
    email: str = "me@example.org"
    password: str = "s3cret"
    avisos: list[dict[str, Any]] = field(default_factory=list)
    places: dict[str, dict[str, Any]] = field(default_factory=dict)
    refuse_own_reiteration: bool = False
    create_status: int = 200
    slack_ok: bool = True
    calls: list[tuple[str, str, Any]] = field(default_factory=list)
    _next: int = 9900000

    def add(
        self,
        address: str,
        *,
        status: str = "initial_node",
        supporting: bool = False,
        requested: str = "2026-09-26T10:00:00+00:00",
    ) -> dict[str, Any]:
        self._next += 1
        aviso = {
            "token": f"tok{self._next}",
            "service_request_id": str(self._next),
            "address": address,
            "status_node_type": status,
            "status_node": {"visible_name": "Asignado" if status == "initial_node" else "Cerrado"},
            "supporting": supporting,
            "requested_datetime": requested,
        }
        self.avisos.append(aviso)
        return aviso

    def place(self, address: str) -> None:
        self.places[address] = {
            "formatted_address": address,
            "location": {"lat": 40.37, "lng": -3.61},
            "data": [
                {"question": {"id": "q-via"}, "value": "Calle"},
                {"question": {"id": "q-portal"}, "value": "  "},
                {"question": {"id": "q-cp"}, "value": 28001},
                {"question": {"id": "q-dist"}, "value": None},
            ],
        }

    def posted(self, path: str) -> list[Any]:
        return [body for method, p, body in self.calls if method == "POST" and p == path]

    def request(
        self, method: str, url: str, *, headers: dict[str, str], body: bytes | None = None
    ) -> Response:
        parts = urllib.parse.urlsplit(url)
        query = dict(urllib.parse.parse_qsl(parts.query))
        if url.startswith("https://slack.com/"):
            self.calls.append((method, "slack", json.loads(body or b"{}")))
            return _json({"ok": self.slack_ok, "error": None if self.slack_ok else "bad"})
        if url == LOGIN:
            return self._login(method, body)
        path = url.removeprefix(API).split("?", 1)[0]
        if headers.get("Authorization") != f"Bearer {TOKEN}":
            return _json([{"code": 401, "description": "Unauthorized"}], 401)
        decoded: Any = None
        if body is not None:
            ctype = headers.get("Content-Type", "")
            decoded = json.loads(body) if ctype == "application/json" else _form(body, ctype)
        self.calls.append((method, path, decoded))
        return self._route(method, path, query, decoded)

    def _login(self, method: str, body: bytes | None) -> Response:
        if method == "GET":
            return Response(200, b"<form>")
        form = dict(urllib.parse.parse_qsl((body or b"").decode()))
        if form.get("user_mail") == self.email and form.get("password") == self.password:
            where = f"https://avisos.madrid.es/es.madrid/?token={TOKEN}&refresh_token=r"
            return Response(302, b"", {"Location": where})
        return Response(200, b"<p>Credenciales incorrectas</p>")

    def _route(self, method: str, path: str, query: dict[str, str], body: Any) -> Response:
        if (method, path) == ("GET", "/me"):
            return _json({"first_name": "Ana", "last_name": "Pi", "email": self.email})
        if (method, path) == ("GET", "/requests") and query.get("own") == "true":
            return _json(self.avisos)
        if method == "GET" and path.startswith("/requests/"):
            token = path.rsplit("/", 1)[1]
            return _json([a for a in self.avisos if a["token"] == token])
        if (method, path) == ("GET", "/location-additional-data"):
            hit = self.places.get(query.get("formatted_address", ""))
            return (
                _json([hit])
                if hit
                else _json([{"code": 404, "description": "Object not found"}], 404)
            )
        if (method, path) == ("POST", "/requests"):
            if self.create_status != 200:
                return _json(
                    [{"code": self.create_status, "description": "limit"}], self.create_status
                )
            aviso = self.add(body["address_string"], requested="2026-09-27T03:30:00+00:00")
            return _json(
                [{"token": aviso["token"], "service_request_id": aviso["service_request_id"]}]
            )
        if m := re.fullmatch(r"/request/(\w+)/reiteration", path):
            aviso = next(a for a in self.avisos if a["token"] == m[1])
            if self.refuse_own_reiteration:
                return _json([{"code": 400, "description": "own request"}], 400)
            aviso["supporting"] = True
            return _json({"ok": True})
        if (method, path) == ("POST", "/requests_comments"):
            return _json([{"id": "c1"}])
        return _json([{"code": 404, "description": f"no route {method} {path}"}], 404)


def _json(payload: Any, status: int = 200) -> Response:
    return Response(status, json.dumps(payload).encode(), {"Content-Type": "application/json"})


def _form(body: bytes, ctype: str) -> dict[str, str]:
    boundary = ctype.split("boundary=", 1)[1]
    out = {}
    for chunk in body.decode().split(f"--{boundary}"):
        if m := re.search(r'name="([^"]+)"\r\n\r\n(.*)\r\n$', chunk, re.S):
            out[m[1]] = m[2]
    return out
