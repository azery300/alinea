import os

import psycopg
import pytest

from alinea.db import connect

pytestmark = pytest.mark.db


@pytest.fixture
def conn():
    try:
        c = connect()
    except psycopg.OperationalError as exc:
        # In CI the database must be there; locally, skip with a hint.
        if os.environ.get("CI"):
            raise
        pytest.skip(f"Postgres not reachable, run `make db-up` ({exc})")
    yield c
    c.close()


def test_pgvector_cosine_distance(conn):
    # Same direction, different length: cosine distance is 0.
    (distance,) = conn.execute("SELECT '[1,2,3]'::vector <=> '[2,4,6]'::vector").fetchone()
    assert distance == pytest.approx(0.0)
