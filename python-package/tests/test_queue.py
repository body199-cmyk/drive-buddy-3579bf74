from teledrive.queue_manager import QueueManager

QUEUE = QueueManager()
from teledrive.models import MediaItem
from teledrive import database as db

# Actions proven by this module (see teledrive/action_registry.proof_test):
PROVES = (
    "analyze.enqueue_selected",
)


def _mk(sk, name="a.bin", size=100):
    return MediaItem(source_key=sk, chat_id=1, message_id=1, file_unique_id="u",
                     original_name=name, safe_name=name, media_type="document",
                     extension="bin", size_bytes=size)


def test_enqueue_and_deduplicate():
    a = QUEUE.enqueue(_mk("tg:1:1:x"))
    b = QUEUE.enqueue(_mk("tg:1:1:x"))
    assert a.id == b.id


def test_transition_records_event():
    it = QUEUE.enqueue(_mk("tg:1:2:x"))
    QUEUE.transition(it.id, "Analyzing")
    QUEUE.transition(it.id, "Skipped")
    assert db.get_item(it.id).state == "Skipped"


def test_priority():
    it = QUEUE.enqueue(_mk("tg:1:3:x"))
    QUEUE.set_priority(it.id, 1)
    items = db.list_items()
    assert items[0].id == it.id
