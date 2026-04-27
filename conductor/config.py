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

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields in .env


settings = Settings()
