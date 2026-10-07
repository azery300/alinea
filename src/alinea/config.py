"""Application settings, read from environment variables and the local .env file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://alinea:alinea@localhost:5432/alinea"
    # Raw sources and caches, gitignored.
    data_dir: Path = Path("data")

    # Embeddings (Mistral API). mistral-embed has a fixed output size of 1024.
    mistral_api_key: str = ""
    embedding_model: str = "mistral-embed"
    embedding_dim: int = 1024


def get_settings() -> Settings:
    return Settings()
