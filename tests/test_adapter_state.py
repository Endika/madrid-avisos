import json

import pytest

from madrid_avisos.adapters.state import JsonStateFile

MAYOR = "Calle Mayor, 26"


def test_a_missing_file_is_a_first_morning(tmp_path):
    assert JsonStateFile(tmp_path / "state.json").load() == {}


def test_the_state_survives_a_round_trip_and_stays_readable(tmp_path):
    path = tmp_path / "state.json"
    store = JsonStateFile(path)

    store.save({MAYOR: "t1", "Calle de Toledo, 29": "t2"})

    assert JsonStateFile(path).load() == {MAYOR: "t1", "Calle de Toledo, 29": "t2"}
    assert '"Calle Mayor, 26": "t1"' in path.read_text()
    assert list(tmp_path.iterdir()) == [path]


def test_saving_replaces_what_was_there(tmp_path):
    store = JsonStateFile(tmp_path / "state.json")
    store.save({MAYOR: "t1"})

    store.save({MAYOR: "t2"})

    assert store.load() == {MAYOR: "t2"}


def test_values_come_back_as_text(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(json.dumps({MAYOR: 9900001}))

    assert JsonStateFile(path).load() == {MAYOR: "9900001"}


def test_a_corrupt_file_is_an_error_not_a_blank_slate(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{nope")

    with pytest.raises(ValueError):
        JsonStateFile(path).load()
