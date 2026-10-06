"""Load the Code du travail into the `articles` table: `uv run python -m alinea.ingest`."""

from alinea import articles, legi
from alinea.config import get_settings
from alinea.db import connect
from alinea.parsing import parse_code


def main() -> None:
    settings = get_settings()
    path = legi.download_code(settings.data_dir)
    result = parse_code(legi.load_code(path))
    print(f"legi-data {legi.LEGI_DATA_VERSION}: {len(result.articles)} articles kept")
    print(f"{len(result.skipped)} skipped:")
    for reason in result.skipped:
        print(f"  {reason}")

    with connect() as conn:
        articles.create_table(conn)
        articles.replace_articles(conn, result.articles)
        stats = articles.length_stats(conn)

    print("\nText length in characters:")
    print("| Part | Articles | Min | Median | p90 | p99 | Max | Mean |")
    print("|---|---|---|---|---|---|---|---|")
    for row in stats:
        print("| " + " | ".join(str(v) for v in row) + " |")


if __name__ == "__main__":
    main()
