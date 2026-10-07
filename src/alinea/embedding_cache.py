"""On-disk embedding cache: a text that did not change is never embedded twice."""

import hashlib
import sqlite3
from array import array
from pathlib import Path

from alinea.config import Settings
from alinea.llm import Embedder, MistralEmbedder, Task


class CachedEmbedder:
    """Wraps an Embedder. Vectors live in a SQLite file, keyed by model, dimension, task and
    text, so changing any of them gives a cache miss instead of a wrong vector."""

    def __init__(self, embedder: Embedder, path: Path, commit_every: int = 100) -> None:
        self.embedder = embedder
        self.model = embedder.model
        self.dim = embedder.dim
        self.commit_every = commit_every
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS embeddings (key TEXT PRIMARY KEY, vector BLOB)")
        self.misses = 0  # texts sent to the embedder, for reporting

    def key(self, text: str, task: Task) -> str:
        raw = "\0".join([self.model, str(self.dim), task, text])
        return hashlib.sha256(raw.encode()).hexdigest()

    def embed(self, texts: list[str], task: Task) -> list[list[float]]:
        keys = [self.key(text, task) for text in texts]
        vectors = self._lookup(keys)

        # Texts not in the cache, each one once even if it appears several times.
        missing = {k: text for k, text in zip(keys, texts, strict=True) if k not in vectors}
        items = list(missing.items())
        # Commit every few batches, so an interrupted run (rate limit, crash) keeps its work.
        for start in range(0, len(items), self.commit_every):
            group = items[start : start + self.commit_every]
            new = self.embedder.embed([text for _, text in group], task)
            self.misses += len(group)
            for (k, _), vector in zip(group, new, strict=True):
                vectors[k] = vector
                self.db.execute(
                    "INSERT OR REPLACE INTO embeddings VALUES (?, ?)",
                    (k, array("f", vector).tobytes()),
                )
            self.db.commit()
        return [vectors[k] for k in keys]

    def _lookup(self, keys: list[str]) -> dict[str, list[float]]:
        found: dict[str, list[float]] = {}
        unique = list(dict.fromkeys(keys))
        for start in range(0, len(unique), 500):  # stay under SQLite's parameter limit
            batch = unique[start : start + 500]
            marks = ",".join("?" * len(batch))
            rows = self.db.execute(
                f"SELECT key, vector FROM embeddings WHERE key IN ({marks})", batch
            )
            for k, blob in rows:
                found[k] = array("f", blob).tolist()
        return found


def get_embedder(settings: Settings) -> CachedEmbedder:
    """The configured embedder, behind the on-disk cache."""
    mistral = MistralEmbedder(
        settings.mistral_api_key, settings.embedding_model, settings.embedding_dim
    )
    return CachedEmbedder(mistral, settings.data_dir / "cache" / "embeddings.sqlite")
