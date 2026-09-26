from email.parser import BytesParser
from email.policy import default

import pytest

from madrid_avisos.adapters.http import Response
from madrid_avisos.adapters.portal.client import PortalClient, PortalError, encode_multipart
from madrid_avisos.adapters.portal.parsing import (
    aviso_from_api,
    error_detail,
    exact_match,
    login_token,
    place_from_api,
)

from .fakes import FakeMadrid

MAYOR = "Calle Mayor, 26"


def hit(address: str, *, location: bool = True) -> dict[str, object]:
    return {
        "formatted_address": address,
        "location": {"lat": 40.41, "lng": -3.70} if location else None,
    }


def test_the_login_token_rides_in_the_redirect():
    res = Response(302, headers={"Location": "https://x/?token=jwt-1&expires_in=2592000"})

    assert login_token(res) == "jwt-1"


def test_the_login_token_is_found_whatever_the_header_case():
    assert login_token(Response(303, headers={"location": "/?token=jwt-1"})) == "jwt-1"


@pytest.mark.parametrize(
    "res",
    [
        Response(200, b"<p>Credenciales incorrectas</p>"),
        Response(200, headers={"Location": "/?token=jwt-1"}),
        Response(302, headers={"Location": "/login?error=1"}),
        Response(302),
    ],
)
def test_no_redirect_with_a_token_means_no_login(res):
    assert login_token(res) == ""


def test_the_geocoder_match_ignores_case_only():
    assert exact_match(MAYOR, [hit("CALLE MAYOR, 26")]) == hit("CALLE MAYOR, 26")


@pytest.mark.parametrize(
    "candidates",
    [
        None,
        [],
        [hit("Calle Mayor, 28")],
        [hit("Calle Mayor, 26 ")],
        [hit(MAYOR, location=False)],
        [hit(MAYOR), hit("calle mayor, 26")],
    ],
    ids=["nothing", "empty", "next-door", "stray-space", "no-location", "two-exact"],
)
def test_the_geocoder_never_guesses(candidates):
    assert exact_match(MAYOR, candidates) is None


def test_a_place_keeps_only_the_answers_with_a_value():
    place = place_from_api(
        {
            **hit(MAYOR),
            "data": [
                {"question": {"id": "q-via"}, "value": "Calle"},
                {"question": {"id": "q-portal"}, "value": "  "},
                {"question": {"id": "q-cp"}, "value": 28001},
                {"question": {"id": "q-dist"}, "value": None},
            ],
        }
    )

    assert (place.address, place.lat, place.lng) == (MAYOR, 40.41, -3.70)
    assert place.data == (("q-via", "Calle"), ("q-cp", 28001))


def test_an_aviso_falls_back_to_the_fields_the_portal_sometimes_uses_instead():
    aviso = aviso_from_api(
        {"token": "t1", "address_string": MAYOR, "status_node": {"name": "Recibido"}}
    )

    assert (aviso.address, aviso.status_name, aviso.number) == (MAYOR, "Recibido", "")
    assert aviso.is_open


def test_a_final_status_closes_the_aviso():
    assert not aviso_from_api({"token": "t1", "status_node_type": "final_ok_node"}).is_open


def test_an_error_shows_the_portals_own_description():
    res = Response(429, b'[{"code": 429, "description": "limit"}]')

    assert error_detail(res) == "limit"
    assert error_detail(Response(502, b"<html>Bad gateway</html>")) == "<html>Bad gateway</html>"


def test_a_comment_is_a_multipart_form_any_parser_reads_back():
    body, ctype = encode_multipart({"description": "Sigue sucia, ¿y mañana?", "token": "t1"})

    message = BytesParser(policy=default).parsebytes(
        f"Content-Type: {ctype}\r\n\r\n".encode() + body
    )
    fields = {}
    for part in message.iter_parts():
        payload = part.get_payload(decode=True)
        assert isinstance(payload, bytes)
        fields[part.get_param("name", header="content-disposition")] = payload.decode()

    assert fields == {"description": "Sigue sucia, ¿y mañana?", "token": "t1"}


def test_every_comment_gets_its_own_boundary():
    assert encode_multipart({"a": "1"})[1] != encode_multipart({"a": "1"})[1]


def test_the_informant_is_only_what_the_profile_actually_fills_in():
    portal = PortalClient(FakeMadrid(), "me@example.org", "s3cret")
    portal.login()

    assert portal.informant() == {"first_name": "Ana", "last_name": "Pi", "email": "me@example.org"}


def test_an_aviso_the_portal_does_not_have_looks_up_as_none():
    portal = PortalClient(FakeMadrid(), "me@example.org", "s3cret")
    portal.login()

    assert portal.lookup("tok-unknown") is None


def test_a_wrong_password_says_so():
    portal = PortalClient(FakeMadrid(), "me@example.org", "wrong")

    with pytest.raises(PortalError, match="wrong email or password"):
        portal.login()


def test_a_broken_profile_is_reported_as_the_informant():
    portal = PortalClient(FakeMadrid(html_on="/me"), "me@example.org", "s3cret")
    portal.login()

    with pytest.raises(PortalError, match=r"^informant: HTTP 200 not JSON"):
        portal.informant()
