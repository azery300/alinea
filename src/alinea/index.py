"""Build the V1 retrieval index: `uv run python -m alinea.index`.

`--measure-tokens` measures the characters-per-token ratio of the corpus with the tokenizer of
the embedding model, which turns the chunk size in tokens into a size in characters.
"""

import argparse
import random
import time

import psycopg

from alinea import articles, retrieval
from alinea.chunking import Chunk, fixed_size_chunks
from alinea.config import get_settings
from alinea.db import connect
from alinea.embedding_cache import CachedEmbedder, get_embedder
from alinea.llm import MistralEmbedder

# V1 chunk size from the spec: about 500 tokens, 50 tokens of overlap.
CHUNK_TOKENS = 500
OVERLAP_TOKENS = 50
# Measured with `--measure-tokens` (see DECISIONS.md, step 2).
CHARS_PER_TOKEN = 3.25


def build_v1(conn: psycopg.Connection, embedder: CachedEmbedder) -> list[Chunk]:
    size = round(CHUNK_TOKENS * CHARS_PER_TOKEN)
    overlap = round(OVERLAP_TOKENS * CHARS_PER_TOKEN)
    chunks = fixed_size_chunks(articles.load_texts(conn), size, overlap)
    vectors = embedder.embed([c.text for c in chunks], task="document")
    retrieval.create_table(conn, embedder.dim)
    retrieval.replace_chunks(conn, "v1", chunks, vectors)
    return chunks


def measure_chars_per_token(conn: psycopg.Connection, sample_size: int = 300) -> None:
    # The Mistral API has no token counting endpoint: embed the sample (not cached) and read
    # the token count the API reports.
    settings = get_settings()
    embedder = MistralEmbedder(
        settings.mistral_api_key, settings.embedding_model, settings.embedding_dim
    )
    texts = [text for _, text in articles.load_texts(conn)]
    sample = random.Random(0).sample(texts, sample_size)  # fixed seed: same sample every run
    chars = sum(len(t) for t in sample)
    embedder.embed(sample, task="document")
    print(f"{sample_size} articles: {chars} chars, {embedder.tokens} tokens")
    print(f"chars per token: {chars / embedder.tokens:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measure-tokens", action="store_true")
    args = parser.parse_args()

    with connect() as conn:
        if args.measure_tokens:
            measure_chars_per_token(conn)
            return
        embedder = get_embedder(get_settings())
        started = time.perf_counter()
        chunks = build_v1(conn, embedder)
        elapsed = time.perf_counter() - started
    lengths = sorted(len(c.text) for c in chunks)
    print(f"v1: {len(chunks)} chunks, {embedder.misses} embedded, {elapsed:.0f}s")
    print(f"chunk length (chars): median {lengths[len(lengths) // 2]}, max {lengths[-1]}")
    mean_articles = sum(len(c.article_nums) for c in chunks) / len(chunks)
    print(f"articles per chunk (mean): {mean_articles:.1f}")


if __name__ == "__main__":
    main()
