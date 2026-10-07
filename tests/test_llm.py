from types import SimpleNamespace

import pytest

from alinea.llm import MistralEmbedder


class FakeEmbeddings:
    def __init__(self, drop=0, dim=3):
        self.requests = []
        self.drop = drop
        self.dim = dim

    def create(self, model, inputs):
        self.requests.append(SimpleNamespace(model=model, inputs=inputs))
        n = len(inputs) - self.drop
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.1] * self.dim)] * n,
            usage=SimpleNamespace(prompt_tokens=10 * len(inputs)),
        )


def make_embedder(embeddings, batch_size=64):
    embedder = MistralEmbedder("fake-key", "mistral-embed", 3, batch_size=batch_size)
    embedder.client = SimpleNamespace(embeddings=embeddings)
    return embedder


def test_sends_texts_unchanged_and_counts_tokens():
    embeddings = FakeEmbeddings()
    embedder = make_embedder(embeddings)
    vectors = embedder.embed(["a", "b"], "query")
    [request] = embeddings.requests
    # mistral-embed is symmetric: no task prefix, whatever the task.
    assert request.inputs == ["a", "b"]
    assert request.model == "mistral-embed"
    assert vectors == [[0.1] * 3, [0.1] * 3]
    assert embedder.tokens == 20


def test_batching():
    embeddings = FakeEmbeddings()
    make_embedder(embeddings, batch_size=2).embed(["a", "b", "c"], "document")
    assert [r.inputs for r in embeddings.requests] == [["a", "b"], ["c"]]


def test_raises_when_the_api_returns_fewer_vectors():
    with pytest.raises(RuntimeError, match="sent 2 texts, got 1"):
        make_embedder(FakeEmbeddings(drop=1)).embed(["a", "b"], "document")


def test_raises_on_unexpected_dimension():
    with pytest.raises(RuntimeError, match="expected dimension 3, got 5"):
        make_embedder(FakeEmbeddings(dim=5)).embed(["a"], "document")


def test_missing_api_key_is_explicit():
    with pytest.raises(ValueError, match="MISTRAL_API_KEY"):
        MistralEmbedder("", "mistral-embed", 1024)
