import pytest

pytestmark = pytest.mark.db


def test_pgvector_cosine_distance(conn):
    # Same direction, different length: cosine distance is 0.
    (distance,) = conn.execute("SELECT '[1,2,3]'::vector <=> '[2,4,6]'::vector").fetchone()
    assert distance == pytest.approx(0.0)
