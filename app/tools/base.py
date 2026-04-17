from __future__ import annotations

from typing import Protocol


class Tool(Protocol):
    name: str

    def run(self, user_input: str) -> str:
        ...
