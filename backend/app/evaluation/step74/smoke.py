from __future__ import annotations

from dataclasses import dataclass

from app.ai.llm.openai_provider import OpenAILLMProvider

from .contracts import GENERATOR_MODEL, JUDGE_MODEL
from .eligibility import select_eligible_cases
from .judge import OpenAIResponsesGenerationJudge, expected_judge_request_identity


@dataclass(frozen=True)
class RuntimeSmokeEvidence:
    settings_preflight: str
    generator_smoke: dict
    judge_smoke: dict
    source: str = "REAL_API"

    def validate(self, *, allow_test_fake: bool = False) -> None:
        source_valid = self.source == "REAL_API" or (allow_test_fake and self.source == "TEST_FAKE")
        if not source_valid or self.settings_preflight != "PASS":
            raise RuntimeError("STEP74_REAL_SMOKE_GATE_REQUIRED")
        generator = self.generator_smoke
        if (generator.get("status") != "PASS" or generator.get("provider") != "openai"
                or generator.get("model") != GENERATOR_MODEL
                or type(generator.get("api_calls")) is not int or generator.get("api_calls") < 1):
            raise RuntimeError("STEP74_GENERATOR_SMOKE_REQUIRED")
        if generator.get("config") != {
            "model": GENERATOR_MODEL, "temperature": 0.2, "max_output_tokens": 800,
            "reasoning_effort": "none", "tools": [],
        }:
            raise RuntimeError("STEP74_GENERATOR_SMOKE_IDENTITY_MISMATCH")
        judge = self.judge_smoke
        if (judge.get("status") != "PASS" or judge.get("provider") != "OpenAI API"
                or judge.get("api") != "Responses API" or judge.get("model") != JUDGE_MODEL
                or judge.get("reasoning_effort") != "none" or judge.get("temperature") != 0
                or judge.get("max_output_tokens") != 1600 or judge.get("structured_output") is not True
                or judge.get("tools") != [] or type(judge.get("api_calls")) is not int
                or judge.get("api_calls") < 1):
            raise RuntimeError("STEP74_JUDGE_SMOKE_REQUIRED")

    def artifact(self, *, allow_test_fake: bool = False) -> dict:
        self.validate(allow_test_fake=allow_test_fake)
        return {
            "source": self.source,
            "settings_preflight": self.settings_preflight,
            "generator": self.generator_smoke,
            "judge": self.judge_smoke,
            "status": "PASS",
            "total_api_calls": self.generator_smoke["api_calls"] + self.judge_smoke["api_calls"],
        }


def validate_settings_preflight(settings, generation_config) -> None:
    if settings.app_env not in {"development", "test", "production"} or type(settings.debug) is not bool:
        raise RuntimeError("STEP74_SETTINGS_PREFLIGHT_FAILED")
    if settings.llm_provider != "openai" or settings.llm_model != GENERATOR_MODEL \
            or generation_config.model != GENERATOR_MODEL:
        raise RuntimeError("STEP74_GENERATOR_MODEL_MISMATCH")
    credential = settings.llm_api_key
    if credential is None or not credential.get_secret_value().strip():
        raise RuntimeError("STEP74_GENERATOR_CREDENTIAL_UNAVAILABLE")


async def run_real_smoke_gate(runner) -> RuntimeSmokeEvidence:
    """Make one real production generator and D-100 judge call before official Stage A."""
    validate_settings_preflight(runner.settings, runner.generation_config)
    if not isinstance(runner.generation_service.provider, OpenAILLMProvider):
        raise RuntimeError("STEP74_GENERATOR_SMOKE_REQUIRES_PRODUCTION_PROVIDER")
    if not isinstance(runner.judge, OpenAIResponsesGenerationJudge):
        raise RuntimeError("STEP74_JUDGE_SMOKE_REQUIRES_D100_PROVIDER")
    _, cases = select_eligible_cases()
    case = next(item for item in cases if item["split"] == "DEVELOPMENT")
    generated = await runner.generate_case(case, run_id="step74-smoke-preflight")
    if generated["generator"]["status"] != "SUCCESS":
        raise RuntimeError("STEP74_GENERATOR_SMOKE_FAILED")
    generator_config = {
        "model": runner.generation_config.model,
        "temperature": runner.generation_config.temperature,
        "max_output_tokens": runner.generation_config.max_output_tokens,
        "reasoning_effort": runner.generation_config.reasoning_effort,
        "tools": [],
    }
    if (generated["generator"].get("provider") != "openai"
            or generated["generator"].get("model") != GENERATOR_MODEL
            or generator_config["model"] != GENERATOR_MODEL or generator_config["tools"] != []):
        raise RuntimeError("STEP74_GENERATOR_SMOKE_IDENTITY_MISMATCH")
    judge_call = await runner.judge.evaluate(
        case, generated["generated_answer"], generated["fixed_evidence"]
    )
    judge_result = getattr(judge_call, "result", judge_call)
    judge_result.validate_evidence_ids(case["case_id"], set(generated["fixed_evidence_ids"]))
    judge_config = runner.judge.last_request_identity
    if judge_config != expected_judge_request_identity():
        raise RuntimeError("STEP74_JUDGE_SMOKE_IDENTITY_MISMATCH")
    generator_calls = generated["generator"].get("attempt_count") or 1
    judge_calls = getattr(judge_call, "attempt_count", 1)
    evidence = RuntimeSmokeEvidence(
        settings_preflight="PASS",
        generator_smoke={"status": "PASS", "provider": "openai", "model": GENERATOR_MODEL,
                         "config": generator_config, "api_calls": generator_calls},
        judge_smoke={"status": "PASS", "provider": "OpenAI API", "api": "Responses API",
                     **judge_config, "api_calls": judge_calls},
    )
    evidence.validate()
    return evidence
