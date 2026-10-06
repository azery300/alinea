from datetime import date

import pytest

from alinea.articles import create_table, length_stats, replace_articles
from alinea.parsing import Article

pytestmark = pytest.mark.db


def make_article(num, text):
    return Article(
        id=f"LEGIARTI-{num}",
        cid=f"CID-{num}",
        num=num,
        text=text,
        breadcrumb=("Partie législative", "Livre Ier"),
        status="VIGUEUR",
        valid_from=date(2008, 5, 1),
        valid_to=None,
        nota="",
    )


@pytest.fixture
def table(conn):
    # A throwaway schema, so the tests never touch the real `articles` table.
    conn.execute("DROP SCHEMA IF EXISTS test_articles CASCADE")
    conn.execute("CREATE SCHEMA test_articles")
    conn.execute("SET search_path TO test_articles")
    create_table(conn)
    yield conn
    conn.rollback()
    conn.execute("DROP SCHEMA test_articles CASCADE")
    conn.commit()


def test_replace_articles_round_trip(table):
    replace_articles(table, [make_article("L1", "Un.\nDeux."), make_article("R2", "Trois")])
    row = table.execute("SELECT text, breadcrumb, url FROM articles WHERE num = 'L1'").fetchone()
    assert row == (
        "Un.\nDeux.",
        ["Partie législative", "Livre Ier"],
        "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI-L1",
    )


def test_replace_articles_is_idempotent(table):
    replace_articles(table, [make_article("L1", "Un.")])
    replace_articles(table, [make_article("L1", "Un.")])
    assert table.execute("SELECT count(*) FROM articles").fetchone() == (1,)


def test_length_stats_per_part_and_overall(table):
    replace_articles(table, [make_article("L1", "abc"), make_article("R2", "abcdefg")])
    stats = {row[0]: row[1:] for row in length_stats(table)}
    assert stats["L"][:2] == (1, 3)  # count, min length
    assert stats["all"][0] == 2
    assert stats["all"][-2] == 7  # max length
