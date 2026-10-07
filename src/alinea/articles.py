"""The `articles` table: one row per article in force."""

from collections.abc import Iterable

import psycopg

from alinea.parsing import Article

SCHEMA = """
CREATE TABLE articles (
    num         text PRIMARY KEY,       -- e.g. L1221-19
    position    integer NOT NULL UNIQUE, -- order in the code
    id          text NOT NULL UNIQUE,   -- LEGIARTI id of the version in force
    cid         text NOT NULL,          -- id shared by all versions
    part        char(1) NOT NULL CHECK (part IN ('L', 'R', 'D')),
    text        text NOT NULL,          -- one paragraph (alinea) per line
    breadcrumb  text[] NOT NULL,
    status      text NOT NULL,
    valid_from  date NOT NULL,
    valid_to    date,                   -- NULL when no end date is planned
    nota        text NOT NULL,
    url         text NOT NULL
)
"""

COLUMNS = "num, position, id, cid, part, text, breadcrumb, status, valid_from, valid_to, nota, url"


def create_table(conn: psycopg.Connection) -> None:
    """(Re)create the table. The ingest reloads everything anyway, so the schema always
    matches the code and no migration is needed."""
    conn.execute("DROP TABLE IF EXISTS articles")
    conn.execute(SCHEMA)
    conn.commit()


def replace_articles(conn: psycopg.Connection, articles: Iterable[Article]) -> None:
    """Replace the whole table in one transaction: readers never see a half-loaded code."""
    with conn.cursor() as cur:
        cur.execute("TRUNCATE articles")
        with cur.copy(f"COPY articles ({COLUMNS}) FROM STDIN") as copy:
            for position, a in enumerate(articles):
                copy.write_row(
                    (a.num, position, a.id, a.cid, a.part, a.text, list(a.breadcrumb), a.status,
                     a.valid_from, a.valid_to, a.nota, a.url)
                )  # fmt: skip
    conn.commit()


def load_texts(conn: psycopg.Connection) -> list[tuple[str, str]]:
    """(num, text) of every article, in code order."""
    return conn.execute("SELECT num, text FROM articles ORDER BY position").fetchall()


def length_stats(conn: psycopg.Connection) -> list[tuple]:
    """Article count and text length distribution (characters), per part and overall."""
    return conn.execute(
        """
        SELECT coalesce(part::text, 'all') AS scope,
               count(*),
               min(length(text)),
               percentile_disc(0.5) WITHIN GROUP (ORDER BY length(text)),
               percentile_disc(0.9) WITHIN GROUP (ORDER BY length(text)),
               percentile_disc(0.99) WITHIN GROUP (ORDER BY length(text)),
               max(length(text)),
               round(avg(length(text)))::int
        FROM articles
        GROUP BY ROLLUP (part)
        ORDER BY grouping(part), part
        """
    ).fetchall()
