import pytest

from aiforus.services.presence import Presence, Verdict, parse_presence

YES, NO, UNSURE = Verdict.YES, Verdict.NOT_VISIBLE, Verdict.UNSURE


@pytest.mark.parametrize(
    "reply, expected",
    [
        (
            '{"visible": "yes", "clock": 10, "detail": "di samping gelas"}',
            Presence(YES, 10, "di samping gelas"),
        ),
        ('{"visible": "yes", "clock": "1", "detail": ""}', Presence(YES, 1, "")),
        ('{"visible": "no", "clock": null, "detail": ""}', Presence(NO)),
        ('{"visible": "unsure", "clock": null, "detail": ""}', Presence(UNSURE)),
        # tolerated: code fences, chatter around the object, trailing period
        ('```json\n{"visible": "yes", "clock": 12, "detail": "di meja."}\n```', Presence(YES, 12, "di meja")),
        ('Berikut jawabannya: {"visible":"no","clock":null,"detail":""} semoga membantu', Presence(NO)),
    ],
)
def test_well_formed_replies(reply, expected):
    assert parse_presence(reply) == expected


@pytest.mark.parametrize(
    "reply",
    [
        # The Windows test, as JSON: "not visible" but it describes where it is.
        '{"visible": "no", "clock": 10, "detail": ""}',
        '{"visible": "no", "clock": null, "detail": "ada kunci di atas meja"}',
        # "yes" whose description says the opposite
        '{"visible": "yes", "clock": 10, "detail": "tidak ada kunci"}',
        '{"visible": "yes", "clock": 12, "detail": "I cannot see it clearly"}',
        # not a verdict / not JSON at all
        '{"visible": "maybe", "clock": 12}',
        "Tidak terlihat. Ada kunci di atas meja.",
        "",
        "[1, 2, 3]",
        '{"visible": "yes", "clock": 12',
    ],
)
def test_contradictions_and_garbage_become_unsure(reply):
    assert parse_presence(reply) == Presence(UNSURE)


def test_yes_keeps_only_front_clock_positions_and_short_details():
    assert parse_presence('{"visible": "yes", "clock": 6, "detail": "di bawah"}') == Presence(
        YES, None, "di bawah"
    )
    rambling = " ".join(["kata"] * 20)
    assert parse_presence(f'{{"visible": "yes", "clock": 2, "detail": "{rambling}"}}') == Presence(YES, 2, "")
