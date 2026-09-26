from __future__ import annotations

import json
from pathlib import Path

import pytest

from madrid_avisos.cli import main

from .fakes import FakeMadrid

MAYOR = "Calle Mayor, 26"
PEZ = "Calle del Pez, 24"
TOLEDO = "Calle de Toledo, 29"


@pytest.fixture
def home(tmp_path: Path) -> Path:
    (tmp_path / "credentials").write_text("email=me@example.org\npassword=s3cret\n")
    (tmp_path / "config.toml").write_text(
        f'streets = ["{MAYOR}", "{PEZ}", "{TOLEDO}"]\n'
        "[aviso]\n"
        'description = "Calle llena de basura."\n'
        'followup = "Sigue sucia."\n'
        "[slack]\n"
        'token = "xoxb-1"\nchannel = "C1"\n'
    )
    return tmp_path


@pytest.fixture
def madrid() -> FakeMadrid:
    fake = FakeMadrid()
    for street in (MAYOR, PEZ, TOLEDO):
        fake.place(street)
    return fake


def tick(home: Path, madrid: FakeMadrid, *extra: str) -> int:
    return main(["--config", str(home / "config.toml"), *extra], transport=madrid)


def slack_text(madrid: FakeMadrid) -> str:
    return str(madrid.posted("slack")[-1]["text"])


def state(home: Path) -> dict[str, str]:
    return dict(json.loads((home / "state.json").read_text()))


def test_first_morning_adopts_open_avisos_on_the_same_street_and_opens_the_rest(home, madrid):
    pez = madrid.add("Calle del Pez, 26")
    old_toledo = madrid.add("Calle de Toledo, 41", requested="2026-09-26T09:00:00+00:00")
    new_toledo = madrid.add("Calle de Toledo, 27", requested="2026-09-26T11:00:00+00:00")

    assert tick(home, madrid) == 0

    [created] = madrid.posted("/requests")
    assert created["address_string"] == MAYOR
    assert created["description"] == "Calle llena de basura."
    assert created["additionalData"] == [
        {"question": "6422b7d4a95195461e8b459e", "value": "Suciedad"}
    ]
    assert created["location_additional_data"] == [
        {"question": "q-via", "value": "Calle"},
        {"question": "q-cp", "value": 28001},
    ]
    assert (created["first_name"], created["email"]) == ("Ana", "me@example.org")
    assert madrid.posted(f"/request/{pez['token']}/reiteration") == [
        {
            "description": "Sigue sucia.",
            "source": "5922d3a24e4ea82f178b4567",
            "follow_request": "true",
        }
    ]
    assert madrid.posted(f"/request/{new_toledo['token']}/reiteration")
    assert not madrid.posted(f"/request/{old_toledo['token']}/reiteration")
    assert state(home) == {
        MAYOR: madrid.avisos[-1]["token"],
        PEZ: pez["token"],
        TOLEDO: new_toledo["token"],
    }
    text = slack_text(madrid)
    assert f"{MAYOR}: aviso nuevo #{madrid.avisos[-1]['service_request_id']}" in text
    assert f"{PEZ}: reiterado #{pez['service_request_id']} (Asignado)" in text


def test_once_reiterated_the_next_mornings_comment(home, madrid):
    for street in (MAYOR, PEZ, TOLEDO):
        madrid.add(street)
    tick(home, madrid)
    madrid.calls.clear()

    assert tick(home, madrid) == 0

    comments = madrid.posted("/requests_comments")
    assert [c["description"] for c in comments] == ["Sigue sucia."] * 3
    assert {c["token"] for c in comments} == {a["token"] for a in madrid.avisos}
    assert not madrid.posted("/requests")
    assert slack_text(madrid).count("comentado") == 3


def test_a_refused_reiteration_falls_back_to_a_comment_and_says_so(home, madrid):
    aviso = madrid.add(PEZ)
    madrid.refuse_own_reiteration = True

    assert tick(home, madrid) == 0

    assert madrid.posted("/requests_comments")[0]["token"] == aviso["token"]
    assert "comentado" in slack_text(madrid)
    assert "reiterar rechazado" in slack_text(madrid)


def test_a_closed_aviso_is_replaced_and_its_closing_reported(home, madrid):
    aviso = madrid.add(PEZ)
    tick(home, madrid)
    aviso["status_node_type"] = "final_ok_node"
    aviso["status_node"] = {"visible_name": "Resuelto"}
    madrid.calls.clear()

    tick(home, madrid)

    addresses = [c["address_string"] for c in madrid.posted("/requests")]
    assert PEZ in addresses
    assert state(home)[PEZ] != aviso["token"]
    assert f"el anterior #{aviso['service_request_id']} se cerró: Resuelto" in slack_text(madrid)


def test_a_refused_creation_fails_loudly_without_stopping_the_other_streets(home, madrid):
    madrid.add(PEZ)
    madrid.create_status = 429

    assert tick(home, madrid) == 1

    text = slack_text(madrid)
    assert f"{MAYOR}: ERROR" in text
    assert "HTTP 429" in text
    assert f"{PEZ}: reiterado" in text
    assert MAYOR not in state(home)


def test_an_address_the_geocoder_cannot_pin_is_an_error_not_a_guess(home, madrid):
    del madrid.places[TOLEDO]

    assert tick(home, madrid) == 1

    assert TOLEDO not in [c["address_string"] for c in madrid.posted("/requests")]
    assert f"{TOLEDO}: ERROR" in slack_text(madrid)


def test_a_wrong_password_is_reported_to_slack(home, madrid):
    madrid.password = "changed"

    assert tick(home, madrid) == 1

    assert "no se ha podido empezar" in slack_text(madrid)
    assert not (home / "state.json").exists()


def test_dry_run_sends_nothing_and_keeps_no_state(home, madrid, capsys):
    madrid.add(PEZ)

    assert tick(home, madrid, "--dry-run") == 0

    assert [m for m, _, _ in madrid.calls] == ["GET"] * len(madrid.calls)
    assert not (home / "state.json").exists()
    out = capsys.readouterr().out
    assert "simulado, no se ha enviado nada" in out
    assert f"{MAYOR}: aviso nuevo, simulado" in out


def test_missing_credentials_stop_before_touching_the_network(home, madrid):
    (home / "credentials").unlink()

    assert tick(home, madrid) == 2

    assert madrid.calls == []


def test_a_slack_refusal_keeps_the_state_but_exits_non_zero(home, madrid):
    madrid.slack_ok = False

    assert tick(home, madrid) == 1

    assert (home / "state.json").exists()


def test_a_server_error_on_reiteration_fails_the_street_instead_of_commenting(home, madrid):
    madrid.add(PEZ)
    madrid.reiteration_status = 503

    assert tick(home, madrid) == 1

    assert not madrid.posted("/requests_comments")
    assert f"{PEZ}: ERROR" in slack_text(madrid)


def test_a_network_failure_mid_run_still_reaches_slack(home, madrid):
    madrid.add(PEZ)
    madrid.network_down_on = "/request/"

    assert tick(home, madrid) == 1

    text = slack_text(madrid)
    assert f"{PEZ}: ERROR" in text
    assert "network" in text
    assert f"{MAYOR}: aviso nuevo" in text


def test_a_page_that_is_not_json_is_reported_not_a_crash(home, madrid):
    madrid.html_on = "/me"

    assert tick(home, madrid) == 1

    assert "not JSON" in slack_text(madrid)


def test_a_corrupt_state_file_is_reported_before_sending_anything(home, madrid):
    (home / "state.json").write_text("{nope")

    assert tick(home, madrid) == 1

    assert not madrid.posted("/requests")
    assert "no se ha podido empezar" in slack_text(madrid)


def test_two_addresses_on_one_street_never_share_an_aviso(home, madrid):
    config = home / "config.toml"
    config.write_text(config.read_text().replace(TOLEDO, "Calle del Pez, 30"))
    madrid.place("Calle del Pez, 30")
    tick(home, madrid)
    first = state(home)
    closed = next(a for a in madrid.avisos if a["token"] == first[PEZ])
    closed["status_node_type"] = "final_ok_node"
    madrid.calls.clear()

    tick(home, madrid)

    after = state(home)
    assert after[PEZ] != after["Calle del Pez, 30"]
    assert after["Calle del Pez, 30"] == first["Calle del Pez, 30"]
    assert PEZ in [c["address_string"] for c in madrid.posted("/requests")]


def test_an_aviso_created_but_not_yet_readable_is_tracked_not_failed(home, madrid):
    madrid.hide_new = True

    assert tick(home, madrid) == 0

    assert len(madrid.posted("/requests")) == 3
    assert set(state(home).values()) == {a["token"] for a in madrid.avisos}
    assert "ERROR" not in slack_text(madrid)


def test_a_tracked_aviso_off_the_list_is_looked_up_before_opening_another(home, madrid):
    aviso = madrid.add(PEZ)
    tick(home, madrid)
    madrid.unlisted.add(aviso["token"])
    madrid.calls.clear()

    tick(home, madrid)

    assert PEZ not in [c["address_string"] for c in madrid.posted("/requests")]
    assert madrid.posted("/requests_comments")[0]["token"] == aviso["token"]


def test_creation_accepts_any_2xx(home, madrid):
    madrid.create_ok_status = 201

    assert tick(home, madrid) == 0

    assert len(madrid.posted("/requests")) == 3


def test_an_unreachable_slack_does_not_crash_but_exits_non_zero(home, madrid):
    madrid.network_down_on = "slack"

    assert tick(home, madrid) == 1

    assert (home / "state.json").exists()
