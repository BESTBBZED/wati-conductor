"""Configuration management — loads settings from environment and ``.env`` file."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All runtime settings, populated from env vars or ``.env``."""

    # WATI API Configuration
    wati_api_endpoint: str = ""  # e.g., https://live-mt-server.wati.io
    wati_token: str = ""

    # Mode
    use_mock: bool = True
    dry_run_default: bool = False

    # LLM Configuration — ReAct agent model
    llm_react_model: str = "deepseek-v4-pro"
    max_react_iterations: int = 10

    # Legacy model routing (kept for backward compat, unused by ReAct graph)
    llm_parse_model: str = "deepseek-v4-flash"
    llm_plan_model: str = "deepseek-v4-flash"
    llm_clarify_model: str = "deepseek-v4-flash"

    # API Keys
    deepseek_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # LLM Settings
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096

    # Rate Limiting
    max_requests_per_second: int = 10
    max_concurrent_requests: int = 5

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "conductor"
    postgres_password: str = "conductor"
    postgres_db: str = "wati_conductor"

    # Knowledge Base
    kb_enabled: bool = True
    kb_embedding_model: str = "all-MiniLM-L6-v2"
    kb_embedding_dim: int = 384
    kb_top_k: int = 5
    kb_chunk_size: int = 512
    kb_chunk_overlap: int = 64

    # Skills
    skills_enabled: bool = True

    # Logging
    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        """Build async PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
