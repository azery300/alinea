"""Dense search from the command line: `uv run python -m alinea.search "question"`."""

import argparse

from alinea import retrieval
from alinea.config import get_settings
from alinea.db import connect
from alinea.embedding_cache import get_embedder


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("-k", type=int, default=5)
    parser.add_argument("--version", default="v1")
    args = parser.parse_args()

    embedder = get_embedder(get_settings())
    with connect() as conn:
        hits = retrieval.search(conn, embedder, args.query, args.version, args.k)
    for rank, hit in enumerate(hits, 1):
        preview = " ".join(hit.text.split())[:300]
        print(f"{rank}. score {hit.score:.3f}  articles {', '.join(hit.article_nums)}")
        print(f"   {preview}\n")


if __name__ == "__main__":
    main()
