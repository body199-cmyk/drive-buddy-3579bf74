import pytest
from teledrive.telegram_links import parse, InvalidLink


def test_public_message():
    p = parse("https://t.me/somechannel/123")
    assert p.kind == "public"
    assert p.chat == "somechannel"
    assert p.message_id == 123


def test_private_channel():
    p = parse("https://t.me/c/1234567890/50")
    assert p.kind == "private"
    assert p.chat == -1001234567890
    assert p.message_id == 50


def test_invite():
    p = parse("https://t.me/+abcdef")
    assert p.kind == "invite"
    assert p.chat == "abcdef"


def test_saved():
    p = parse("saved")
    assert p.kind == "saved"


def test_username_only():
    p = parse("https://t.me/somechannel")
    assert p.kind == "username_only"


def test_invalid():
    with pytest.raises(InvalidLink):
        parse("http://example.com/x")
    with pytest.raises(InvalidLink):
        parse("")


@pytest.mark.parametrize(
    ("value", "kind", "chat", "message_id"),
    [
        ("@somechannel", "username_only", "somechannel", None),
        ("t.me/somechannel/123?single", "public", "somechannel", 123),
        (
            "https://www.telegram.me/s/somechannel/123#comment",
            "public",
            "somechannel",
            123,
        ),
        ("https://t.me/somechannel?boost=1", "username_only", "somechannel", None),
        ("https://telegram.me/joinchat/abcdef", "invite", "abcdef", None),
        ("https://t.me/c/1234567890", "private", -1001234567890, None),
        ("https://t.me/c/1234567890/50?comment=1", "private", -1001234567890, 50),
    ],
)
def test_common_copied_link_spellings(value, kind, chat, message_id):
    parsed = parse(value)
    assert parsed.kind == kind
    assert parsed.chat == chat
    assert parsed.message_id == message_id
    assert parsed.raw == value


def test_lookalike_host_is_still_refused():
    with pytest.raises(InvalidLink):
        parse("https://t.me.example.com/somechannel/123")
