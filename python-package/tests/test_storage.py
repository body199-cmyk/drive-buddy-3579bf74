from teledrive.storage_manager import temp_path_for, cleanup_item


def test_temp_and_cleanup():
    p = temp_path_for("id123", "a.bin")
    p.write_bytes(b"x")
    assert p.exists()
    cleanup_item("id123")
    assert not p.exists()
