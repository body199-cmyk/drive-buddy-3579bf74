from teledrive.error_handler import classify


def test_floodwait():
    class E(Exception):
        seconds = 12
    e = E("FloodWaitError 12s")
    r = classify(e)
    assert r.code == "TG_FLOOD_WAIT" and r.is_transient


def test_reauth():
    r = classify(Exception("session expired"))
    assert r.category == "reauth" and not r.retryable


def test_transient():
    r = classify(TimeoutError("network timeout"))
    assert r.is_transient


def test_permanent():
    r = classify(Exception("invalid link"))
    assert r.category == "permanent"
