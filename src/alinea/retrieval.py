"""The `chunks` table and dense search over it."""

from dataclasses import dataclass

import psycopg

from alinea.chunking import Chunk
from alinea.llm import Embedder

# One table for every retrieval version, so V1 and V2 can be measured on the same database.
# No vector index on purpose: ORDER BY on the distance scans every row, so the search is an exact
# k-NN (100% recall of the nearest chunks). With a few thousand chunks the scan stays fast.
SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    version       text NOT NULL,      -- retrieval version: v1 (fixed size), v2 (structural)
    position      integer NOT NULL,   -- order of the chunk in the code
    text          text NOT NULL,
    article_nums  text[] NOT NULL,    -- articles the chunk overlaps
    embedding     vector({dim}) NOT NULL,
    PRIMARY KEY (version, position)
)
"""


@dataclass(frozen=True)
class Hit:
    text: str
    article_nums: list[str]
    score: float  # cosine similarity, 1 = same direction


def to_pgvector(vector: list[float]) -> str:
    """pgvector's text format, so no extra adapter library is needed."""
    return "[" + ",".join(str(x) for x in vector) + "]"


def create_table(conn: psycopg.Connection, dim: int) -> None:
    conn.execute(SCHEMA.format(dim=dim))
    conn.commit()


def replace_chunks(
    conn: psycopg.Connection, version: str, chunks: list[Chunk], vectors: list[list[float]]
) -> None:
    """Replace every chunk of one version in a single transaction."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM chunks WHERE version = %s", (version,))
        with cur.copy(
            "COPY chunks (version, position, text, article_nums, embedding) FROM STDIN"
        ) as copy:
            for position, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
                copy.write_row(
                    (version, position, chunk.text, list(chunk.article_nums), to_pgvector(vector))
                )
    conn.commit()


def search(
    conn: psycopg.Connection, embedder: Embedder, query: str, version: str = "v1", k: int = 5
) -> list[Hit]:
    """Top-k chunks by cosine similarity to the query (exact k-NN)."""
    [vector] = embedder.embed([query], task="query")
    rows = conn.execute(
        """
        SELECT text, article_nums, 1 - (embedding <=> %(q)s::vector) AS score
        FROM chunks
        WHERE version = %(version)s
        ORDER BY embedding <=> %(q)s::vector
        LIMIT %(k)s
        """,
        {"q": to_pgvector(vector), "version": version, "k": k},
    ).fetchall()
    return [Hit(text, nums, score) for text, nums, score in rows]
