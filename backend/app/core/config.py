import logging
import math
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import make_url


Environment = Literal["development", "test", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
TRUSTED_EXTERNAL_DOMAINS = (
    "www.open.edu",
    "en.wiktionary.org",
    "www.chinesetest.cn",
)


class Settings(BaseSettings):
    """Typed application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    app_name: str = "Trung Chinese Learning API"
    app_env: Environment = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    database_url: str | None = None
    test_database_url: str | None = None
    secret_key: SecretStr = Field(min_length=1)
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    log_level: LogLevel = "DEBUG"
    access_token_expire_minutes: int = Field(default=30, gt=0)
    refresh_token_expire_days: int = Field(default=7, gt=0)
    password_reset_expire_minutes: int = Field(default=30, gt=0)
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict"] = "lax"
    document_max_upload_mb: int = Field(default=20, gt=0)
    document_storage_root: Path = Path("storage/documents")
    embedding_provider: Literal["local"] = "local"
    embedding_model_name: Literal["BAAI/bge-m3"] = "BAAI/bge-m3"
    embedding_model_revision: Literal["5617a9f61b028005a4858fdac845db406aefb181"] = "5617a9f61b028005a4858fdac845db406aefb181"
    embedding_device: Literal["auto", "cpu", "cuda", "mps"] = "auto"
    embedding_batch_size: int = Field(default=32, gt=0)
    embedding_input_version: Literal["v1"] = "v1"
    embedding_normalize: bool = True
    rag_retrieval_candidate_k: int = Field(default=20, ge=1, le=100)
    rag_evidence_calibration_mode: bool = False
    rag_min_rerank_score: float | None = None
    external_retrieval_provider: Literal["tavily"] = "tavily"
    external_retrieval_base_url: Literal["https://api.tavily.com"] = "https://api.tavily.com"
    external_retrieval_api_key: SecretStr | None = None
    external_retrieval_k: int = Field(default=10, ge=10, le=10)
    external_retrieval_allowed_domains: Annotated[tuple[str, ...], NoDecode] = TRUSTED_EXTERNAL_DOMAINS
    external_retrieval_request_timeout_seconds: float = Field(default=10.0, gt=0)
    rag_memory_max_turns: int = Field(default=3, ge=0, le=3)
    reranker_provider: Literal["local"] = "local"
    reranker_model_name: Literal["BAAI/bge-reranker-v2-m3"] = "BAAI/bge-reranker-v2-m3"
    reranker_model_revision: Literal["953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"] = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
    reranker_device: Literal["auto", "cpu", "cuda", "mps"] = "auto"
    reranker_batch_size: int = Field(default=8, ge=1, le=20)
    reranker_top_k: int = Field(default=5, ge=1, le=5)
    reranker_input_version: Literal["v1"] = "v1"
    llm_provider: Literal["openai"] = "openai"
    llm_model: Literal["gpt-5.4-mini-2026-03-17"] = "gpt-5.4-mini-2026-03-17"
    llm_api_key: SecretStr | None = None
    llm_request_timeout_seconds: float = Field(default=60, gt=0)
    llm_max_transient_retries: int = Field(default=1, ge=0, le=1)
    llm_max_output_tokens: int = Field(default=800, ge=1, le=800)
    llm_temperature: float = 0.2
    llm_reasoning_effort: Literal["none"] = "none"
    llm_model_input_limit: int = 400_000
    ai_generation_max_questions: int = Field(default=10, ge=1, le=10)
    ai_generation_max_output_tokens: int = Field(default=4000, ge=1, le=4000)

    @field_validator("rag_memory_max_turns", mode="before")
    @classmethod
    def reject_boolean_memory_turn_limit(cls, value: object) -> object:
        # bool is an int subclass in Python, but is not a meaningful turn cap.
        if isinstance(value, bool):
            raise ValueError("RAG_MEMORY_MAX_TURNS must be an integer from 0 to 3")
        return value

    @field_validator("rag_min_rerank_score", mode="before")
    @classmethod
    def validate_rag_min_rerank_score(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError("RAG_MIN_RERANK_SCORE must be a finite number")
        try:
            parsed = float(value)
        except (TypeError, ValueError, OverflowError):
            raise ValueError("RAG_MIN_RERANK_SCORE must be a finite number") from None
        if not math.isfinite(parsed):
            raise ValueError("RAG_MIN_RERANK_SCORE must be a finite number")
        return parsed

    @field_validator("external_retrieval_allowed_domains", mode="before")
    @classmethod
    def parse_external_retrieval_allowed_domains(cls, value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            values = value.split(",")
        elif isinstance(value, (tuple, list)):
            values = value
        else:
            raise ValueError("EXTERNAL_RETRIEVAL_ALLOWED_DOMAINS must be comma-separated")
        if not all(isinstance(item, str) for item in values):
            raise ValueError("EXTERNAL_RETRIEVAL_ALLOWED_DOMAINS must contain hostnames")
        normalized = tuple(dict.fromkeys(item.strip().lower().removesuffix(".") for item in values if item.strip()))
        if frozenset(normalized) != frozenset(TRUSTED_EXTERNAL_DOMAINS):
            raise ValueError("EXTERNAL_RETRIEVAL_ALLOWED_DOMAINS must match the frozen D-094 allowlist")
        return normalized

    @field_validator("external_retrieval_k", mode="before")
    @classmethod
    def require_frozen_external_retrieval_k(cls, value: object) -> int:
        if value == 10 or (isinstance(value, str) and value.strip() == "10"):
            return 10
        raise ValueError("EXTERNAL_RETRIEVAL_K must be exactly 10")

    @field_validator("llm_temperature")
    @classmethod
    def require_frozen_llm_temperature(cls, value: float) -> float:
        if value != 0.2:
            raise ValueError("LLM_TEMPERATURE must be 0.2 for V0")
        return value

    @field_validator("llm_model_input_limit")
    @classmethod
    def require_frozen_llm_input_limit(cls, value: int) -> int:
        if value != 400_000:
            raise ValueError("LLM_MODEL_INPUT_LIMIT must be 400000 for V0")
        return value

    @field_validator("ai_generation_max_questions")
    @classmethod
    def require_frozen_ai_generation_max_questions(cls, value: int) -> int:
        if value != 10:
            raise ValueError("AI_GENERATION_MAX_QUESTIONS must be 10 for V0")
        return value

    @field_validator("ai_generation_max_output_tokens")
    @classmethod
    def require_frozen_ai_generation_output_budget(cls, value: int) -> int:
        if value != 4000:
            raise ValueError("AI_GENERATION_MAX_OUTPUT_TOKENS must be 4000 for V0")
        return value

    @field_validator("embedding_normalize")
    @classmethod
    def require_embedding_normalization(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("EMBEDDING_NORMALIZE must be true for V0")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            origins = value.split(",")
        elif isinstance(value, (list, tuple)):
            origins = value
        else:
            raise ValueError("CORS_ORIGINS must be a comma-separated string or list")

        if not all(isinstance(origin, str) for origin in origins):
            raise ValueError("CORS_ORIGINS entries must be strings")

        normalized = [origin.strip() for origin in origins if origin.strip()]
        for origin in normalized:
            if origin == "*":
                raise ValueError("Wildcard CORS origins are not allowed")
            parsed = urlsplit(origin)
            try:
                port = parsed.port
            except ValueError as exc:
                raise ValueError("CORS_ORIGINS contains an invalid origin") from exc
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
                or (port is not None and not 1 <= port <= 65535)
            ):
                raise ValueError("CORS_ORIGINS entries must be HTTP(S) origins")

        return normalized

    @model_validator(mode="after")
    def validate_environment_settings(self) -> "Settings":
        if self.app_env == "production" and self.debug:
            raise ValueError("DEBUG must be disabled in production")

        if "*" in self.cors_origins:
            raise ValueError("Wildcard CORS origins are not allowed")

        if self.app_env == "production":
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be enabled in production")
            if len(self.secret_key.get_secret_value()) < 32:
                raise ValueError("SECRET_KEY must contain at least 32 characters in production")

        if self.app_env == "test":
            if not self.test_database_url:
                raise ValueError("TEST_DATABASE_URL is required when APP_ENV=test")
            if self.database_url and self._database_identity(self.database_url) == self._database_identity(self.test_database_url):
                raise ValueError(
                    "DATABASE_URL and TEST_DATABASE_URL must differ in test mode"
                )

        if self.app_env != "test" and not self.database_url:
            raise ValueError("DATABASE_URL is required outside APP_ENV=test")

        for name, value in (("DATABASE_URL", self.database_url), ("TEST_DATABASE_URL", self.test_database_url)):
            if value is None:
                continue
            try:
                parsed = make_url(value)
            except Exception as exc:
                raise ValueError(f"{name} must be a valid PostgreSQL+psycopg URL") from exc
            if parsed.drivername != "postgresql+psycopg":
                raise ValueError(f"{name} must use the postgresql+psycopg driver")

        return self

    @staticmethod
    def _database_identity(value: str) -> tuple[str, str | None, int]:
        parsed = make_url(value)
        # PostgreSQL assigns port 5432 when callers omit it from the DSN.
        port = parsed.port if parsed.port is not None else 5432
        return parsed.host or "", parsed.database, port

    @property
    def effective_database_url(self) -> str:
        """Return the database URL selected for this application environment."""
        value = self.test_database_url if self.app_env == "test" else self.database_url
        if not value:
            raise ValueError("A database URL is required for the selected environment")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance for this process."""
    return Settings()


def configure_application_logging(settings: Settings) -> None:
    """Apply the configured level to application loggers."""
    logging.getLogger("app").setLevel(settings.log_level)
