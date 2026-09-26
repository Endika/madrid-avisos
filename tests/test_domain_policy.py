from madrid_avisos.domain import Aviso, policy
from madrid_avisos.domain.policy import CommentOn, OpenNew

MAYOR = "Calle Mayor, 26"
PEZ = "Calle del Pez, 24"


def aviso(
    token: str,
    address: str = PEZ,
    *,
    closed: bool = False,
    requested: str = "2026-09-26T10:00:00+00:00",
) -> Aviso:
    return Aviso(
        token=token,
        number=token.upper(),
        address=address,
        status_type="final_ok_node" if closed else "initial_node",
        status_name="Resuelto" if closed else "Asignado",
        requested=requested,
    )


def test_an_open_tracked_aviso_gets_the_comment():
    mine = aviso("t1")

    assert policy.decide(PEZ, {PEZ: "t1"}, [aviso("t0"), mine]) == CommentOn(mine)


def test_a_tracked_aviso_found_only_by_lookup_still_gets_the_comment():
    found = aviso("t1")

    assert policy.decide(PEZ, {PEZ: "t1"}, [], looked_up=found) == CommentOn(found)


def test_a_closed_tracked_aviso_with_nothing_to_adopt_opens_a_new_one_naming_it():
    old = aviso("t1", closed=True)

    assert policy.decide(PEZ, {PEZ: "t1"}, [old]) == OpenNew(closed=old)


def test_a_closed_tracked_aviso_hands_over_to_an_open_one_on_the_same_street():
    old = aviso("t1", closed=True)
    other = aviso("t2", "Calle del Pez, 30")

    assert policy.decide(PEZ, {PEZ: "t1"}, [old, other]) == CommentOn(other, closed=old)


def test_a_tracked_aviso_the_portal_no_longer_has_is_not_reported_as_closed():
    assert policy.decide(PEZ, {PEZ: "gone"}, [], looked_up=None) == OpenNew()


def test_an_untracked_street_adopts_the_newest_open_aviso_on_the_same_street():
    older = aviso("t1", "Calle del Pez, 2", requested="2026-09-26T09:00:00+00:00")
    newer = aviso("t2", "calle del pez, 40", requested="2026-09-26T11:00:00+00:00")
    closed = aviso("t3", requested="2026-09-26T12:00:00+00:00", closed=True)

    assert policy.decide(PEZ, {}, [older, newer, closed]) == CommentOn(newer)


def test_on_equal_dates_the_first_aviso_listed_wins():
    first, second = aviso("t1"), aviso("t2")

    assert policy.decide(PEZ, {}, [first, second]) == CommentOn(first)


def test_an_aviso_on_another_street_is_never_adopted():
    assert policy.decide(PEZ, {}, [aviso("t1", MAYOR)]) == OpenNew()


def test_an_aviso_another_street_tracks_is_never_adopted():
    theirs = aviso("t1", "Calle del Pez, 30")

    assert policy.decide(PEZ, {"Calle del Pez, 30": "t1"}, [theirs]) == OpenNew()


def test_street_name_ignores_the_number_case_and_spacing():
    assert policy.street_name("  Calle del Pez , 24") == policy.street_name("CALLE DEL PEZ, 2")
    assert policy.street_name(MAYOR) != policy.street_name(PEZ)


def test_only_a_tracked_token_missing_from_the_list_needs_a_lookup():
    listed = [aviso("t1")]

    assert policy.unlisted(PEZ, {PEZ: "t9"}, listed) == "t9"
    assert policy.unlisted(PEZ, {PEZ: "t1"}, listed) is None
    assert policy.unlisted(PEZ, {MAYOR: "t9"}, listed) is None
