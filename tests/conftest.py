import os

import psycopg
import pytest

from alinea.db import connect


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
