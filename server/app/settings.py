from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_JOB_JUDGE_", env_file=".env")

    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"
    ranker_provider: str = "claude"
    claude_command: str = "claude"
    claude_model: str = ""
    claude_timeout_seconds: int = 180
    claude_max_budget_usd: float = 0.5
    data_dir: str = "data"
    cors_origins: list[str] = ["chrome-extension://*", "http://127.0.0.1:*", "http://localhost:*"]


settings = Settings()
