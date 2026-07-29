from teledrive.drive_quota import evaluate

# Actions proven by this module (see teledrive/action_registry.proof_test):
PROVES = (
    "drive.refresh_quota",
)


def test_ok():
    r = evaluate({"limit": 100, "usage": 10}, required_bytes=50)
    assert r.ok and not r.warn


def test_warn_90():
    r = evaluate({"limit": 100, "usage": 91}, required_bytes=1)
    assert r.ok and r.warn


def test_insufficient():
    r = evaluate({"limit": 100, "usage": 90}, required_bytes=50)
    assert not r.ok
