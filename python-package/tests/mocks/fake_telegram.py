from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeDoc:
    id: str
    size: int
    mime_type: str = "application/octet-stream"
    attributes: list = field(default_factory=list)


@dataclass
class FakeMsg:
    id: int
    document: Any = None
    photo: Any = None
    date: str = "2026-01-01T00:00:00+00:00"
    grouped_id: Any = None
    media: bool = True


@dataclass
class FakeEntity:
    id: int
    title: str = "fake_chat"
    username: str = "fake"


class FakeTelegram:
    def __init__(self, messages: dict[int, FakeMsg]):
        self.messages = messages
        self.entity = FakeEntity(id=42, title="fake_chat")

    async def get_entity(self, chat):
        return self.entity

    async def get_message(self, chat, mid):
        return self.messages.get(mid)

    async def iter_messages(self, chat, **kw):
        for m in self.messages.values():
            yield m

    async def download_media(self, message, file_path, progress_cb=None):
        from pathlib import Path
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        size = getattr(message.document, "size", 1024) if message.document else 1024
        with open(p, "wb") as f:
            f.write(b"x" * size)
        if progress_cb:
            progress_cb(size, size)
        return str(p)
