from teledrive.filters import FilterSet, apply
from teledrive.models import MediaItem

# Actions proven by this module (see teledrive/action_registry.proof_test):
PROVES = (
    "analyze.apply_filters",
)


def _mk(**kw):
    base = dict(source_key=f"tg:1:{kw.get('message_id',1)}:u", chat_id=1, message_id=1,
                file_unique_id="u", original_name="a.jpg", safe_name="a.jpg",
                media_type="photo", extension="jpg", size_bytes=1000,
                message_date="2026-01-01T00:00:00+00:00")
    base.update(kw)
    return MediaItem(**base)


def test_by_type():
    items = [_mk(media_type="photo"), _mk(media_type="video")]
    assert len(apply(items, FilterSet(media_types={"video"}))) == 1


def test_by_size_range():
    items = [_mk(size_bytes=500), _mk(size_bytes=5000)]
    assert len(apply(items, FilterSet(min_size=1000, max_size=10000))) == 1


def test_include_exclude():
    items = [_mk(original_name="report.pdf", extension="pdf"),
             _mk(original_name="cat.jpg", extension="jpg")]
    r = apply(items, FilterSet(include_substr=["report"]))
    assert len(r) == 1 and r[0].original_name == "report.pdf"
    r = apply(items, FilterSet(exclude_substr=["cat"]))
    assert len(r) == 1


def test_id_range():
    items = [_mk(message_id=5), _mk(message_id=15), _mk(message_id=25)]
    r = apply(items, FilterSet(id_from=10, id_to=20))
    assert len(r) == 1 and r[0].message_id == 15
