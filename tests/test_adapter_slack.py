import logging

from madrid_avisos.adapters.http import Response
from madrid_avisos.adapters.notify.slack import Slack

from .fakes import FakeMadrid


class Answers:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def request(self, method, url, *, headers, body=None):
        return Response(200, self.body)


def test_a_refusal_logs_slacks_error_code_not_the_whole_reply(caplog):
    madrid = FakeMadrid(slack_ok=False)

    with caplog.at_level(logging.ERROR):
        assert not Slack(madrid, "xoxb-1", "C1").send("hola")

    assert "Slack answered an error: bad" in caplog.text
    assert "'ok'" not in caplog.text


def test_json_that_is_not_an_object_is_a_failure():
    assert not Slack(Answers(b"[]"), "xoxb-1", "C1").send("hola")


def test_an_accepted_message_goes_to_the_configured_channel():
    madrid = FakeMadrid()

    assert Slack(madrid, "xoxb-1", "C1").send("hola")

    assert madrid.posted("slack") == [{"channel": "C1", "text": "hola"}]
