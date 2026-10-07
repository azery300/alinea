import pytest

from alinea.embedding_cache import CachedEmbedder


class FakeEmbedder:
    model = "fake"
    dim = 2

    def __init__(self):
        self.calls: list[list[str]] = []

    def embed(self, texts, task):
        self.calls.append(list(texts))
        return [[float(len(t)), 1.0 if task == "query" else 0.0] for t in texts]


@pytest.fixture
def cached(tmp_path):
    fake = FakeEmbedder()
    return CachedEmbedder(fake, tmp_path / "cache.sqlite", commit_every=2), fake


def test_second_call_hits_the_cache(cached):
    embedder, fake = cached
    first = embedder.embed(["un", "deux"], "document")
    second = embedder.embed(["un", "deux"], "document")
    assert first == second == [[2.0, 0.0], [4.0, 0.0]]
    assert fake.calls == [["un", "deux"]]


def test_only_missing_texts_are_embedded_once(cached):
    embedder, fake = cached
    embedder.embed(["un"], "document")
    embedder.embed(["un", "trois", "trois"], "document")
    assert fake.calls == [["un"], ["trois"]]
    assert embedder.misses == 2


def test_task_is_part_of_the_key(cached):
    embedder, fake = cached
    embedder.embed(["un"], "document")
    assert embedder.embed(["un"], "query") == [[2.0, 1.0]]
    assert len(fake.calls) == 2


def test_cache_survives_a_restart(tmp_path):
    path = tmp_path / "cache.sqlite"
    CachedEmbedder(FakeEmbedder(), path).embed(["un"], "document")
    fake = FakeEmbedder()
    assert CachedEmbedder(fake, path).embed(["un"], "document") == [[2.0, 0.0]]
    assert fake.calls == []


def test_misses_are_sent_in_groups(cached):
    embedder, fake = cached  # commit_every=2
    embedder.embed(["a", "b", "c"], "document")
    assert fake.calls == [["a", "b"], ["c"]]
