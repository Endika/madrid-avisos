"""Client for avisos.madrid.es, speaking to its API the way the web app does."""

from __future__ import annotations

import json
import secrets
import urllib.parse
from typing import Any

from .domain import Aviso, Place
from .http import Response, Transport

API = "https://servpub.madrid.es/AVSICAPI"
LOGIN = f"{API}/microservice/login-cid360?origin=SIC"
JURISDICTION = "es.madrid"
JURISDICTION_ELEMENT = "5e5a3f17179796a7cbb93934"
CLIENT_ID = "103ijslkl4g040kko48k8owks44cwcgckw8co804g4c08c0sck"
WEB_CHANNEL = "5922d3a24e4ea82f178b4567"
STREET_CLEANING = "591b126d4e4ea840018b45b6"
# "¿Cuál es el problema?" on the street-cleaning form; the only mandatory question.
PROBLEM_QUESTION = "6422b7d4a95195461e8b459e"
INFORMANT_FIELDS = ("first_name", "last_name", "email", "phone")
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) madrid-avisos"


class PortalError(Exception):
    def __init__(self, what: str, status: int, detail: str = "") -> None:
        super().__init__(f"{what}: HTTP {status} {detail}".rstrip())
        self.status = status


def _aviso(raw: dict[str, Any]) -> Aviso:
    node = raw.get("status_node") or {}
    return Aviso(
        token=str(raw["token"]),
        number=str(raw.get("service_request_id", "")),
        address=str(raw.get("address") or raw.get("address_string") or ""),
        status_type=str(raw.get("status_node_type") or ""),
        status_name=str(node.get("visible_name") or node.get("name") or ""),
        requested=str(raw.get("requested_datetime") or ""),
    )


def _detail(res: Response) -> str:
    try:
        payload = json.loads(res.body)
    except ValueError:
        return res.text()[:200]
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return str(payload[0].get("description") or payload[0])
    return str(payload)[:200]


class Portal:
    def __init__(self, transport: Transport) -> None:
        self._http = transport
        self._token = ""

    def login(self, email: str, password: str) -> None:
        form = urllib.parse.urlencode({"user_mail": email, "password": password}).encode()
        try:
            self._http.request("GET", LOGIN, headers={"User-Agent": USER_AGENT})
            res = self._http.request(
                "POST",
                LOGIN,
                headers={
                    "User-Agent": USER_AGENT,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                body=form,
            )
        except OSError as exc:
            raise PortalError("login", 0, f"network: {exc}") from exc
        location = res.headers.get("Location") or res.headers.get("location") or ""
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(location).query)
        token = query.get("token", [""])[0]
        if res.status not in (301, 302, 303) or not token:
            raise PortalError("login", res.status, "no token; wrong email or password?")
        self._token = token

    def _call(
        self,
        what: str,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
        form: tuple[bytes, str] | None = None,
    ) -> Any:
        url = f"{API}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "es",
            "X-Client-Id": CLIENT_ID,
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode()
        elif form is not None:
            body, headers["Content-Type"] = form
        try:
            res = self._http.request(method, url, headers=headers, body=body)
        except OSError as exc:
            raise PortalError(what, 0, f"network: {exc}") from exc
        if not 200 <= res.status < 300:
            raise PortalError(what, res.status, _detail(res))
        try:
            return json.loads(res.body) if res.body else None
        except ValueError as exc:
            raise PortalError(what, res.status, f"not JSON: {res.text()[:120]!r}") from exc

    def profile(self) -> dict[str, Any]:
        me = self._call("profile", "GET", "/me")
        if not isinstance(me, dict):
            raise PortalError("profile", 200, "unexpected shape")
        return me

    def my_avisos(self) -> list[Aviso]:
        raw = self._call(
            "my avisos",
            "GET",
            "/requests",
            params={
                "jurisdiction_ids": JURISDICTION,
                "service_ids": STREET_CLEANING,
                "own": "true",
                "limit": "90",
            },
        )
        if not isinstance(raw, list) or not all(isinstance(r, dict) and "token" in r for r in raw):
            raise PortalError("my avisos", 200, "unexpected shape")
        return [_aviso(r) for r in raw]

    def aviso(self, token: str) -> Aviso:
        raw = self._call("aviso", "GET", f"/requests/{token}")
        found = raw[0] if isinstance(raw, list) and raw else raw
        if not isinstance(found, dict) or "token" not in found:
            raise PortalError("aviso", 404, f"{token} not found")
        return _aviso(found)

    def locate(self, address: str) -> Place:
        raw = self._call(
            f"locate {address!r}",
            "GET",
            "/location-additional-data",
            params={"jurisdiction_element_id": JURISDICTION_ELEMENT, "formatted_address": address},
        )
        exact = [
            p
            for p in raw or []
            if str(p.get("formatted_address", "")).casefold() == address.casefold()
            and p.get("location")
        ]
        if len(exact) != 1:
            found = [p.get("formatted_address") for p in raw or []]
            raise PortalError(f"locate {address!r}", 200, f"no single exact match: {found}")
        hit = exact[0]
        data = tuple(
            (str(d["question"]["id"]), d["value"])
            for d in hit.get("data", [])
            if d.get("value") is not None and str(d["value"]).strip()
        )
        return Place(
            address=str(hit["formatted_address"]),
            lat=float(hit["location"]["lat"]),
            lng=float(hit["location"]["lng"]),
            data=data,
        )

    def create(
        self, place: Place, *, problem: str, description: str, informant: dict[str, Any]
    ) -> Aviso:
        body: dict[str, Any] = {
            "service_id": STREET_CLEANING,
            "description": description,
            "address_string": place.address,
            "lat": place.lat,
            "long": place.lng,
            "public": True,
            "additionalData": [{"question": PROBLEM_QUESTION, "value": problem}],
            "location_additional_data": [{"question": q, "value": v} for q, v in place.data],
            "device_id": WEB_CHANNEL,
            "device_type": WEB_CHANNEL,
            "jurisdiction_id": JURISDICTION,
        }
        body |= {k: informant[k] for k in INFORMANT_FIELDS if informant.get(k)}
        raw = self._call(
            "create", "POST", "/requests", params={"jurisdiction_id": JURISDICTION}, payload=body
        )
        made = raw[0] if isinstance(raw, list) and raw else raw
        if not isinstance(made, dict) or "token" not in made:
            raise PortalError("create", 200, f"no token in {str(raw)[:120]}")
        try:
            return self.aviso(str(made["token"]))
        except PortalError:
            # It exists; it just is not readable yet. Track it anyway so tomorrow pushes it.
            return Aviso(
                token=str(made["token"]),
                number=str(made.get("service_request_id", "")),
                address=place.address,
                status_type="initial_node",
                status_name="",
                requested="",
            )

    def comment(self, aviso: Aviso, description: str) -> None:
        self._call(
            "comment",
            "POST",
            "/requests_comments",
            params={"jurisdiction_id": JURISDICTION},
            form=_multipart({"description": description, "token": aviso.token}),
        )


def _multipart(fields: dict[str, str]) -> tuple[bytes, str]:
    boundary = f"----madrid-avisos-{secrets.token_hex(8)}"
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
        for name, value in fields.items()
    ]
    body = "".join(parts) + f"--{boundary}--\r\n"
    return body.encode(), f"multipart/form-data; boundary={boundary}"
