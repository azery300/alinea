"""Thin layer over the model provider, so another provider or a local model can be swapped in."""

from typing import Literal, Protocol

from mistralai.client import Mistral
from mistralai.client.utils import BackoffStrategy, RetryConfig

Task = Literal["query", "document"]


class Embedder(Protocol):
    model: str
    dim: int

    def embed(self, texts: list[str], task: Task) -> list[list[float]]: ...


class MistralEmbedder:
    """mistral-embed is symmetric: queries and documents are embedded the same way, so `task`
    is ignored here (the cache still keys on it)."""

    def __init__(self, api_key: str, model: str, dim: int, batch_size: int = 64) -> None:
        if not api_key:
            raise ValueError("MISTRAL_API_KEY is not set (see .env.example)")
        self.model = model
        self.dim = dim
        # 64 chunks of ~2,000 characters is about 40k tokens per request, accepted by the API.
        self.batch_size = batch_size
        self.tokens = 0  # tokens billed by the API, as reported in each response
        # Retries 429 and 5xx responses with exponential backoff (or the Retry-After header):
        # this absorbs the free tier rate limits during indexing.
        retry = RetryConfig(
            "backoff",
            BackoffStrategy(
                initial_interval=2_000, max_interval=60_000, exponent=2, max_elapsed_time=600_000
            ),
            retry_connection_errors=True,
        )
        self.client = Mistral(api_key=api_key, retry_config=retry)

    def embed(self, texts: list[str], task: Task) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            response = self.client.embeddings.create(model=self.model, inputs=batch)
            if len(response.data) != len(batch):
                raise RuntimeError(f"sent {len(batch)} texts, got {len(response.data)} embeddings")
            self.tokens += response.usage.prompt_tokens or 0
            for item in response.data:
                vector = list(item.embedding or [])
                if len(vector) != self.dim:
                    raise RuntimeError(f"expected dimension {self.dim}, got {len(vector)}")
                vectors.append(vector)
        return vectors
