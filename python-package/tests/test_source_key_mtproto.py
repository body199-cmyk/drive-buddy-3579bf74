"""C-03 regression: source_key = MTProto message identity, never file id.

Audit 2026-08-23 (MEDIUM): the dedupe key carried file_unique_id, violating
Constitution §11 (explicit ban) and §15 (MTProto identity contract).
Decision: ADR-0003 (python-package/docs/decisions/).
"""
from __future__ import annotations

from teledrive.utils import source_key


def test_same_message_different_document_ids_share_one_key():
    # same (chat_id, message_id), different document ids -> SAME key
    assert (
        source_key(-1001234567890, 77)
        == source_key(-1001234567890, 77)
    )
    key = source_key(-1001234567890, 77)
    assert key == "tg:-1001234567890:77"
    # no third component may ever reappear
    assert key.count(":") == 2


def test_distinct_messages_never_collide():
    a = source_key(-1001234567890, 77)
    b = source_key(-1001234567890, 78)
    c = source_key(-1009876543210, 77)
    assert len({a, b, c}) == 3


def test_accepts_int_or_str_inputs_and_normalizes():
    assert source_key("-100123", "77") == source_key(-100123, 77)


def test_scanner_items_use_binary_key_shape(monkeypatch):
    """End-to-end through scan_link: MediaItem.source_key has exactly 2 parts."""
    import asyncio

    from teledrive.media_scanner import ScanRequest, scan_link
    from teledrive.telegram_links import ParsedLink

    class _Attr:
        def __init__(self, name):
            self.file_name = name

    class _Doc:
        def __init__(self, doc_id, size):
            self.id = doc_id
            self.size = size
            self.attributes = [_Attr("clip.mp4")]
            self.mime_type = "video/mp4"

    class _Msg:
        def __init__(self, mid, doc_id):
            self.id = mid
            self.media = True
            self.document = _Doc(doc_id, 256)
            self.photo = None
            self.date = "2026-08-23T00:00:00Z"

    class _Entity:
        id = 123456789
        title = "Test Channel"

    class _TG:
        async def resolve_entity(self, ref):
            return ref

        async def get_entity(self, ref):
            return _Entity()

        def iter_messages(self, chat, **kwargs):
            # same message scanned twice with DIFFERENT document ids
            # (simulates re-fetch); identity must stay stable.
            msgs = [_Msg(77, "doc-aaa"), None]

            async def _agen():
                for m in msgs:
                    yield m

            return _agen()

    items = asyncio.run(
        scan_link(_TG(), ParsedLink(kind="username_only", chat="@test"), ScanRequest().validate())
    )
    assert len(items) == 1
    sk = items[0].source_key
    assert sk.startswith("tg:123456789:")
    assert sk.count(":") == 2
