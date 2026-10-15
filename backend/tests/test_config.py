import logging
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def clean_settings_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "APP_NAME",
        "APP_ENV",
        "DEBUG",
        "API_V1_PREFIX",
        "DATABASE_URL",
        "TEST_DATABASE_URL",
        "SECRET_KEY",
        "CORS_ORIGINS",
        "LOG_LEVEL",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "REFRESH_TOKEN_EXPIRE_DAYS",
        "PASSWORD_RESET_EXPIRE_MINUTES",
        "COOKIE_SECURE",
        "COOKIE_SAMESITE",
        "DOCUMENT_MAX_UPLOAD_MB",
        "DOCUMENT_STORAGE_ROOT",
        "EMBEDDING_PROVIDER",
        "RERANKER_PROVIDER",
        "MODAL_TOKEN_ID",
        "MODAL_TOKEN_SECRET",
        "MODAL_ENVIRONMENT",
        "MODAL_BGE_APP_NAME",
        "MODAL_BGE_CLASS_NAME",
        "EMBEDDING_MODEL_NAME",
        "EMBEDDING_MODEL_REVISION",
        "EMBEDDING_DEVICE",
        "EMBEDDING_BATCH_SIZE",
        "EMBEDDING_INPUT_VERSION",
        "EMBEDDING_NORMALIZE",
        "RAG_RETRIEVAL_CANDIDATE_K",
        "RAG_MEMORY_MAX_TURNS",
        "LLM_PROVIDER", "LLM_MODEL", "LLM_API_KEY", "LLM_REQUEST_TIMEOUT_SECONDS",
        "LLM_MAX_TRANSIENT_RETRIES", "LLM_MAX_OUTPUT_TOKENS", "LLM_TEMPERATURE",
        "LLM_REASONING_EFFORT", "LLM_MODEL_INPUT_LIMIT",
        "AI_GENERATION_MAX_QUESTIONS", "AI_GENERATION_MAX_OUTPUT_TOKENS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("APP_NAME", "Trung Chinese Learning API")
    monkeypatch.setenv("API_V1_PREFIX", "/api/v1")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/chinese_learning_runtime_placeholder",
    )
    monkeypatch.setenv(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://test:test@localhost:5432/chinese_learning_test",
    )
    monkeypatch.setenv("CORS_ORIGINS", "http://test-origin.invalid")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("SECRET_KEY", "test-only-signing-key-not-a-deployment-secret-0123456789")
    get_settings.cache_clear()


def make_test_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "app_env": "test",
        "debug": False,
        "test_database_url": "postgresql+psycopg://test:test@localhost/chinese_learning_test",
        "secret_key": "test-only-signing-key-not-a-deployment-secret-0123456789",
    }
    values.update(overrides)
    return Settings(**values)


def test_tests_use_test_environment_and_dedicated_database() -> None:
    settings = get_settings()

    assert os.environ["APP_ENV"] == "test"
    assert settings.app_env == "test"
    assert settings.test_database_url.endswith("chinese_learning_test")


def test_document_ingestion_settings_default_and_validate_upload_limit() -> None:
    assert make_test_settings().document_max_upload_mb == 20
    assert make_test_settings().document_storage_root == Path("storage/documents")
    with pytest.raises(ValidationError):
        make_test_settings(document_max_upload_mb=0)


def test_ai_generation_output_budget_is_separate_and_frozen() -> None:
    settings = make_test_settings()
    assert settings.ai_generation_max_questions == 10
    assert settings.ai_generation_max_output_tokens == 4000
    assert settings.llm_max_output_tokens == 800
    for invalid in (3999, 4001, 800):
        with pytest.raises(ValidationError):
            make_test_settings(ai_generation_max_output_tokens=invalid)


def test_embedding_settings_defaults_and_validation() -> None:
    settings = make_test_settings()
    assert settings.embedding_provider == "local"
    assert settings.embedding_model_name == "BAAI/bge-m3"
    assert settings.embedding_model_revision == "5617a9f61b028005a4858fdac845db406aefb181"
    assert settings.embedding_device == "auto"
    assert settings.embedding_batch_size == 32
    assert settings.embedding_input_version == "v1"
    assert settings.embedding_normalize is True
    for invalid in (
        {"embedding_provider": "remote"}, {"embedding_model_name": "other"},
        {"embedding_model_revision": "main"}, {"embedding_device": "tpu"},
        {"embedding_batch_size": 0}, {"embedding_input_version": "v2"},
        {"embedding_normalize": False},
    ):
        with pytest.raises(ValidationError):
            make_test_settings(**invalid)


@pytest.mark.parametrize("candidate_k", [1, 20, 100])
def test_rag_retrieval_candidate_k_accepts_frozen_range(candidate_k: int) -> None:
    assert make_test_settings(rag_retrieval_candidate_k=candidate_k).rag_retrieval_candidate_k == candidate_k


@pytest.mark.parametrize("candidate_k", [0, -1, 101])
def test_rag_retrieval_candidate_k_rejects_out_of_range(candidate_k: int) -> None:
    with pytest.raises(ValidationError):
        make_test_settings(rag_retrieval_candidate_k=candidate_k)


def test_rag_retrieval_candidate_k_defaults_to_twenty() -> None:
    assert make_test_settings().rag_retrieval_candidate_k == 20


@pytest.mark.parametrize("turns", [0, 1, 2, 3])
def test_rag_memory_max_turns_accepts_frozen_range(turns: int) -> None:
    assert make_test_settings(rag_memory_max_turns=turns).rag_memory_max_turns == turns


@pytest.mark.parametrize("turns", [-1, 4, True, False, "invalid"])
def test_rag_memory_max_turns_rejects_invalid_values(turns) -> None:
    with pytest.raises(ValidationError):
        make_test_settings(rag_memory_max_turns=turns)


def test_rag_memory_max_turns_defaults_to_three_and_is_environment_overridable(monkeypatch) -> None:
    assert make_test_settings().rag_memory_max_turns == 3
    monkeypatch.setenv("RAG_MEMORY_MAX_TURNS", "1")
    assert make_test_settings().rag_memory_max_turns == 1


def test_llm_settings_defaults_and_frozen_controls() -> None:
    settings = make_test_settings()
    assert settings.llm_provider == "openai"
    assert settings.llm_model == "gpt-5.4-mini-2026-03-17"
    assert settings.llm_api_key is None
    assert settings.llm_request_timeout_seconds == 60
    assert settings.llm_max_transient_retries == 1
    assert settings.llm_max_output_tokens == 800
    assert settings.llm_temperature == 0.2
    assert settings.llm_reasoning_effort == "none"
    assert settings.llm_model_input_limit == 400_000


def test_llm_settings_reject_nonfrozen_provider_generation_controls() -> None:
    for values in (
        {"llm_provider": "other"}, {"llm_model": "gpt-5.4-mini"},
        {"llm_request_timeout_seconds": 0}, {"llm_max_transient_retries": 2},
        {"llm_max_output_tokens": 801}, {"llm_temperature": 0.7},
        {"llm_reasoning_effort": "high"}, {"llm_model_input_limit": 200_000},
    ):
        with pytest.raises(ValidationError):
            make_test_settings(**values)


def test_llm_settings_key_is_secret_and_environment_overridable(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "do-not-print-this-test-secret")
    key = make_test_settings().llm_api_key
    assert key is not None
    assert "do-not-print-this-test-secret" not in str(key)
    assert key.get_secret_value() == "do-not-print-this-test-secret"


def test_rag_retrieval_candidate_k_accepts_backend_environment_override(monkeypatch) -> None:
    monkeypatch.setenv("RAG_RETRIEVAL_CANDIDATE_K", "100")
    assert make_test_settings().rag_retrieval_candidate_k == 100


@pytest.mark.parametrize("device", ["auto", "cpu", "cuda", "mps"])
def test_embedding_device_options_are_supported(device: str) -> None:
    assert make_test_settings(embedding_device=device).embedding_device == device


def test_env_example_documents_embedding_settings_without_secrets() -> None:
    contents = Path(".env.example").read_text(encoding="utf-8")
    for name in (
        "EMBEDDING_PROVIDER", "EMBEDDING_MODEL_NAME", "EMBEDDING_MODEL_REVISION",
        "EMBEDDING_DEVICE", "EMBEDDING_BATCH_SIZE", "EMBEDDING_INPUT_VERSION",
        "EMBEDDING_NORMALIZE", "RAG_RETRIEVAL_CANDIDATE_K",
    ):
        assert f"{name}=" in contents
    assert "5617a9f61b028005a4858fdac845db406aefb181" in contents
    assert "replace-this-local-development-secret" in contents


@pytest.mark.parametrize("environment", ["development", "test", "production"])
def test_supported_environments_are_accepted(environment: str) -> None:
    values: dict[str, object] = {"app_env": environment, "debug": False}
    if environment == "test":
        values["test_database_url"] = "postgresql+psycopg://test:test@localhost/learning_test"
    else:
        values["database_url"] = "postgresql+psycopg://test:test@localhost/learning_runtime"
    if environment == "production":
        values.update({
            "cookie_secure": True, "secret_key": "p" * 40,
            "embedding_provider": "modal", "reranker_provider": "modal",
            "modal_token_id": "test-id", "modal_token_secret": "test-secret",
            "modal_environment": "test", "modal_bge_app_name": "test-app",
            "modal_bge_class_name": "BgeInference",
        })

    settings = Settings(_env_file=None, **values)

    assert settings.app_env == environment


def test_unknown_environment_fails_validation() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="staging")


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "Configured Learning API")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEBUG", "false")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Configured Learning API"
    assert settings.debug is False


def test_dotenv_file_is_supported_and_environment_has_priority(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.setenv("APP_NAME", "Name from environment")

    settings = Settings(_env_file=Path(".env.example"))

    assert settings.app_name == "Name from environment"
    assert settings.app_env == "development"


def test_debug_is_typed_as_bool() -> None:
    settings = make_test_settings()

    assert settings.debug is False
    assert isinstance(settings.debug, bool)


def test_invalid_debug_value_fails_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEBUG", "sometimes")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_production_cannot_enable_debug() -> None:
    with pytest.raises(ValidationError, match="DEBUG must be disabled in production"):
        Settings(_env_file=None, app_env="production", debug=True)


def test_api_prefix_has_default_and_can_be_configured() -> None:
    assert make_test_settings().api_v1_prefix == "/api/v1"
    assert make_test_settings(api_v1_prefix="/api/custom").api_v1_prefix == "/api/custom"


def test_cors_origins_are_normalized_from_csv() -> None:
    settings = make_test_settings(
        cors_origins=" http://localhost:5173, ,http://127.0.0.1:5173  "
    )

    assert settings.cors_origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_invalid_cors_collection_fails_validation() -> None:
    with pytest.raises(ValidationError, match="CORS_ORIGINS entries must be strings"):
        make_test_settings(cors_origins=["https://frontend.example", 7])


def test_invalid_cors_origin_shape_fails_validation() -> None:
    with pytest.raises(ValidationError, match=r"HTTP\(S\) origins"):
        make_test_settings(cors_origins="[]")


def test_production_cors_has_no_wildcard_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    config = {
        "_env_file": None, "app_env": "production", "debug": False, "cookie_secure": True,
        "database_url": "postgresql+psycopg://test:test@localhost/production_placeholder",
        "secret_key": "p" * 40, "embedding_provider": "modal", "reranker_provider": "modal",
        "modal_token_id": "test-id", "modal_token_secret": "test-secret", "modal_environment": "test",
        "modal_bge_app_name": "test-app", "modal_bge_class_name": "BgeInference",
    }
    settings = Settings(**config)

    assert settings.cors_origins == []
    with pytest.raises(ValidationError, match="Wildcard CORS origins"):
        Settings(**{**config, "cors_origins": "*"})


@pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
def test_supported_log_levels_are_accepted(level: str) -> None:
    assert make_test_settings(log_level=level).log_level == level


def test_invalid_log_level_fails_validation() -> None:
    with pytest.raises(ValidationError):
        make_test_settings(log_level="TRACE")


def test_secret_is_required() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", debug=False, database_url="postgresql+psycopg://test:test@runtime/db", secret_key=None)


def test_production_requires_long_secret_and_secure_cookie() -> None:
    with pytest.raises(ValidationError, match="at least 32"):
        Settings(_env_file=None, app_env="production", debug=False, database_url="postgresql+psycopg://test:test@runtime/db", secret_key="short", cookie_secure=True)
    with pytest.raises(ValidationError, match="COOKIE_SECURE"):
        Settings(_env_file=None, app_env="production", debug=False, database_url="postgresql+psycopg://test:test@runtime/db", secret_key="test-only-signing-key-not-a-deployment-secret-0123456789")


def test_auth_settings_validation() -> None:
    for name in ("access_token_expire_minutes", "refresh_token_expire_days", "password_reset_expire_minutes"):
        with pytest.raises(ValidationError):
            make_test_settings(**{name: 0})
    with pytest.raises(ValidationError):
        make_test_settings(cookie_samesite="none")
    for same_site in ("lax", "strict"):
        assert make_test_settings(cookie_samesite=same_site).cookie_samesite == same_site


@pytest.mark.parametrize("environment", ["development", "test", "production"])
def test_wildcard_cors_rejected_in_every_auth_environment(environment: str) -> None:
    values = {"app_env": environment, "debug": False, "cors_origins": "*"}
    if environment == "test":
        values["test_database_url"] = "postgresql+psycopg://test:test@localhost/db_test"
    else:
        values["database_url"] = "postgresql+psycopg://test:test@localhost/db_runtime"
    with pytest.raises(ValidationError, match="Wildcard CORS origins"):
        Settings(_env_file=None, **values)


def test_test_environment_requires_dedicated_database_url() -> None:
    with pytest.raises(ValidationError, match="TEST_DATABASE_URL is required"):
        Settings(
            _env_file=None,
            app_env="test",
            debug=False,
            test_database_url=None,
        )


def test_same_database_url_is_rejected_in_test_environment() -> None:
    url = "postgresql+psycopg://test:test@localhost/chinese_learning_test"
    with pytest.raises(ValidationError, match="must differ in test mode"):
        make_test_settings(database_url=url, test_database_url=url)


def test_same_database_url_is_rejected_with_implicit_default_port() -> None:
    runtime_url = "postgresql+psycopg://test:test@localhost:5432/chinese_learning_test"
    test_url = "postgresql+psycopg://test:test@localhost/chinese_learning_test"

    with pytest.raises(ValidationError, match="must differ in test mode"):
        make_test_settings(database_url=runtime_url, test_database_url=test_url)


def test_test_database_url_is_configuration_only() -> None:
    settings = make_test_settings()

    assert settings.test_database_url.startswith("postgresql+psycopg://")
    # Configuration validation does not connect to the database.


def test_effective_database_url_selects_test_database() -> None:
    settings = make_test_settings(
        database_url="postgresql+psycopg://test:test@runtime/learning",
        test_database_url="postgresql+psycopg://test:test@test/chinese_learning_test",
    )

    assert settings.effective_database_url == settings.test_database_url


def test_development_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError, match="DATABASE_URL is required"):
        Settings(_env_file=None, app_env="development", debug=False)


def test_database_url_requires_psycopg_driver() -> None:
    with pytest.raises(ValidationError, match="postgresql\\+psycopg"):
        Settings(
            _env_file=None,
            app_env="development",
            debug=False,
            database_url="postgresql://user:password@localhost/learning",
        )


def test_settings_accessor_returns_cached_instance() -> None:
    first = get_settings()

    assert get_settings() is first


def test_fastapi_consumes_configured_settings_and_cors() -> None:
    settings = make_test_settings(
        app_env="development",
        app_name="Configured API",
        api_v1_prefix="/api/custom",
        cors_origins=["https://frontend.example"],
        log_level="INFO",
    )
    root_logger = logging.getLogger("app")
    previous_level = root_logger.level
    try:
        application = create_app(settings)
        response = TestClient(application).options(
            "/health",
            headers={
                "Origin": "https://frontend.example",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert application.title == "Configured API"
        assert application.debug is False
        assert application.state.api_v1_prefix == "/api/custom"
        assert root_logger.level == logging.INFO
        assert response.headers["access-control-allow-origin"] == "https://frontend.example"
        assert response.headers["access-control-allow-credentials"] == "true"
    finally:
        root_logger.setLevel(previous_level)


def test_modal_configuration_is_conditional_and_production_requires_both_providers():
    base = {
        "_env_file": None, "app_env": "test", "debug": False,
        "test_database_url": "postgresql+psycopg://test:test@localhost/chinese_learning_test",
        "secret_key": "test-only-signing-key",
    }
    local = Settings(**base)
    assert local.embedding_provider == local.reranker_provider == "local"
    with pytest.raises(ValidationError, match="MODAL_TOKEN_ID"):
        Settings(**base, embedding_provider="modal")

    modal_config = {
        **base, "embedding_provider": "modal", "reranker_provider": "modal",
        "modal_token_id": "fake-test-id", "modal_token_secret": "fake-test-secret",
        "modal_environment": "test", "modal_bge_app_name": "test-app",
        "modal_bge_class_name": "BgeInference",
    }
    selected = Settings(**modal_config)
    assert selected.modal_token_id.get_secret_value() == "fake-test-id"

    production = {
        "_env_file": None, "app_env": "production", "debug": False,
        "database_url": "postgresql+psycopg://test:test@localhost/prod_placeholder",
        "secret_key": "p" * 40, "cookie_secure": True,
    }
    with pytest.raises(ValidationError, match="Production must use Modal"):
        Settings(**production)
    production.update({key: value for key, value in modal_config.items()
                       if key not in {"_env_file", "app_env", "debug", "test_database_url", "secret_key"}})
    Settings(**production)
