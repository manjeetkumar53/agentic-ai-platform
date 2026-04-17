from __future__ import annotations


class SearchDocsTool:
    name = "search_docs"

    _knowledge = {
        "cqrs": "CQRS separates write and read models for scalability and isolation.",
        "event sourcing": "Event sourcing stores immutable events and rebuilds state by replay.",
        "latency": "P95 latency is commonly used to capture tail performance.",
        "vector": "Vector search finds semantically similar chunks using embedding distance.",
    }

    def run(self, user_input: str) -> str:
        lowered = user_input.lower()
        hits = [v for k, v in self._knowledge.items() if k in lowered]
        if not hits:
            return "No internal docs found for this prompt."
        return " ".join(hits)
