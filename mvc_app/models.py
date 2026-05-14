from __future__ import annotations

from pathlib import Path

from audio_similarity.search import search_similar


class SearchModel:
    """Model layer for audio similarity search."""

    def __init__(self, index_dir: str | Path) -> None:
        self.index_dir = Path(index_dir)

    def find_similar(self, query_path: str | Path, top_k: int = 5) -> list[dict[str, str | float | int]]:
        return search_similar(query_path, self.index_dir, top_k=top_k)
