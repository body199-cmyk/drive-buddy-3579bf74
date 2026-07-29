import os
from teledrive.config import redact


def test_redaction():
    os.environ["TELEGRAM_API_HASH"] = "supersecret"
    txt = "hash=supersecret in log"
    assert "supersecret" not in redact(txt)
    del os.environ["TELEGRAM_API_HASH"]
