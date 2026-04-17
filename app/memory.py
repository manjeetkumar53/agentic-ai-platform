from __future__ import annotations

from collections import defaultdict

from app.models import StoredMemory


class SessionMemoryStore:
    def __init__(self) -> None:
        self._store: dict[str, dict] = defaultdict(dict)

    def read(self, session_id: str) -> StoredMemory:
        return StoredMemory(session_id=session_id, facts=self._store[session_id])

    def upsert(self, session_id: str, facts: dict) -> None:
        self._store[session_id].update(facts)
