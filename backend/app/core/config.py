from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_env: str = "development"
    app_name: str = "LexQuery"
    app_version: str = "0.1.0"
    debug: bool = False
    secret_key: str

    # API
    api_v1_prefix: str = "/v1"
    allowed_origins: str = "http://localhost:3000"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str) -> str:
        return v

    def get_allowed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    # Database
    postgres_user: str = "lexquery"
    postgres_password: str = "lexquery_dev"
    postgres_db: str = "lexquery"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str
    database_url_sync: str
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Weaviate
    weaviate_url: str = "http://localhost:8080"

    # Auth / JWT
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    api_key_pepper: str

    # AI providers
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    cohere_api_key: str = ""

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "eu-west-2"
    s3_bucket_name: str = "lexquery-documents-dev"
    s3_endpoint_url: str = ""

    # Ingestion
    chunk_size_tokens: int = 512
    chunk_overlap_tokens: int = 128
    embedding_model: str = "text-embedding-3-large"

    # Retrieval
    retrieval_top_k: int = 20
    rerank_top_n: int = 5
    llm_model: str = "claude-sonnet-4-20250514"
    query_cache_ttl_seconds: int = 900

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
