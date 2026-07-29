from tests.mocks.fake_drive import FakeDrive
from teledrive.duplicate_detector import check


def test_no_match():
    d = FakeDrive()
    r = check(d, "tg:1:1:x", 100)
    assert not r.is_duplicate


def test_match_by_key_and_size(tmp_path):
    d = FakeDrive()
    fid = d.ensure_folder("t")
    p = tmp_path / "a.bin"; p.write_bytes(b"y" * 100)
    d.upload_resumable(str(p), "a.bin", fid, "tg:1:1:x")
    r = check(d, "tg:1:1:x", 100)
    assert r.is_duplicate
