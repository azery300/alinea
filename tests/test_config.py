from alinea.config import Settings


def test_database_url_comes_from_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db:5432/x")
    assert Settings(_env_file=None).database_url == "postgresql://u:p@db:5432/x"
