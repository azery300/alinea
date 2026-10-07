import pytest

from alinea import retrieval
from alinea.chunking import Chunk

pytestmark = pytest.mark.db


class FakeEmbedder:
    model = "fake"
    dim = 3

    def embed(self, texts, task):
        return [[1.0, 0.0, 0.0] for _ in texts]


@pytest.fixture
def db(conn):
    # A throwaway schema, so the tests never touch the real `chunks` table.
    conn.execute("DROP SCHEMA IF EXISTS test_retrieval CASCADE")
    conn.execute("CREATE SCHEMA test_retrieval")
    conn.execute("SET search_path TO test_retrieval, public")  # public: the vector type
    retrieval.create_table(conn, dim=3)
    yield conn
    conn.rollback()
    conn.execute("DROP SCHEMA test_retrieval CASCADE")
    conn.commit()


CHUNKS = [Chunk("loin", ("L1",)), Chunk("proche", ("L2", "L3")), Chunk("moyen", ("L4",))]
VECTORS = [[0.0, 1.0, 0.0], [1.0, 0.1, 0.0], [1.0, 1.0, 0.0]]


def test_search_ranks_by_cosine_similarity(db):
    retrieval.replace_chunks(db, "v1", CHUNKS, VECTORS)
    hits = retrieval.search(db, FakeEmbedder(), "question", k=2)
    assert [h.text for h in hits] == ["proche", "moyen"]
    assert hits[0].article_nums == ["L2", "L3"]
    assert hits[0].score == pytest.approx(0.995, abs=1e-3)


def test_versions_are_kept_apart(db):
    retrieval.replace_chunks(db, "v1", CHUNKS, VECTORS)
    retrieval.replace_chunks(db, "v2", CHUNKS[:1], VECTORS[:1])
    retrieval.replace_chunks(db, "v1", CHUNKS[:2], VECTORS[:2])  # reindex v1 only
    counts = dict(db.execute("SELECT version, count(*) FROM chunks GROUP BY 1").fetchall())
    assert counts == {"v1": 2, "v2": 1}
