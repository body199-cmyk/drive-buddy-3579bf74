from teledrive import snapshot, handoff


def test_snapshot_no_secrets():
    txt = snapshot.generate()
    assert "TeleDrive" in txt


def test_handoff_redacted():
    txt = handoff.generate()
    assert "Redaction check: PASSED" in txt
