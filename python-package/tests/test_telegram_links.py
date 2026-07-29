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
