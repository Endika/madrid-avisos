"""Turning the portal's answers into domain values, without touching the network."""

from __future__ import annotations

import json
import urllib.parse
from collections.abc import Iterable
from typing import Any

from ...domain import Aviso, Place
from ..http import Response


def aviso_from_api(raw: dict[str, Any]) -> Aviso:
    node = raw.get("status_node") or {}
    return Aviso(
        token=str(raw["token"]),
        number=str(raw.get("service_request_id", "")),
        address=str(raw.get("address") or raw.get("address_string") or ""),
        status_type=str(raw.get("status_node_type") or ""),
        status_name=str(node.get("visible_name") or node.get("name") or ""),
        requested=str(raw.get("requested_datetime") or ""),
    )


def login_token(res: Response) -> str:
    """The login answers a redirect with the token in its query string, or "" on failure."""
    if res.status not in (301, 302, 303):
        return ""
    location = res.headers.get("Location") or res.headers.get("location") or ""
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(location).query)
    return query.get("token", [""])[0]


def exact_match(address: str, candidates: Iterable[dict[str, Any]] | None) -> dict[str, Any] | None:
    """The one geocoder hit spelled exactly like `address`; a near miss is never a match."""
    exact = [
        p
        for p in candidates or []
        if str(p.get("formatted_address", "")).casefold() == address.casefold()
        and p.get("location")
    ]
    return exact[0] if len(exact) == 1 else None


def place_from(hit: dict[str, Any]) -> Place:
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


def error_detail(res: Response) -> str:
    try:
        payload = json.loads(res.body)
    except ValueError:
        return res.text()[:200]
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        return str(payload[0].get("description") or payload[0])
    return str(payload)[:200]
