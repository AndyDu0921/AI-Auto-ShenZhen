import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Shenzhen AI Agent MVP"
    database_url: str = os.getenv("DATABASE_URL") or (
        "sqlite:////tmp/agent.db" if os.getenv("PORT") else "sqlite:///./agent.db"
    )
    use_mock_llm: bool = True
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    company_name: str = "Demo Export Co., Ltd."
    sales_email: str = "sales@example.com"
    reply_signature: str = "Best regards,\nAI Sales Desk\nDemo Export Co., Ltd."
    max_chunk_chars: int = 800
    chunk_overlap_chars: int = 120
    top_k_chunks: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
