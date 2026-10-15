from __future__ import annotations

import math

from app.ai.modal_bge import ModalBgeClient, ModalBgeError
from app.ai.modal_bge.schemas import CONTRACT_VERSION, RERANKER_MODEL, RERANKER_REVISION
from app.ai.reranking.errors import reranking_error
from app.ai.reranking.schemas import RerankerProviderIdentity
from app.core.config import Settings


class ModalRerankerProvider:
    def __init__(self, settings: Settings, *, client: ModalBgeClient | None = None):
        self.settings = settings
        self.client = client or ModalBgeClient(settings)
        self.identity = RerankerProviderIdentity(
            "MODAL", CONTRACT_VERSION, RERANKER_MODEL, RERANKER_REVISION, "v1"
        )

    @property
    def device(self) -> str:
        return "modal"

    @staticmethod
    def _validate_result(result, operation: str):
        if not isinstance(result, dict) or result.get("ok") is not True:
            code = result.get("error_code") if isinstance(result, dict) else None
            if code == "RERANK_INPUT_TOO_LONG":
                raise reranking_error(code, "A query and passage exceed the reranker input limit.", 422)
            if code == "RERANKER_NOT_AVAILABLE":
                raise reranking_error(code, "The reranker runtime is unavailable.", 503)
            raise reranking_error("INVALID_RERANKER_OUTPUT", "Reranker returned invalid output.")
        if (result.get("contract_version"), result.get("operation"), result.get("model_name"), result.get("model_revision")) != (
            CONTRACT_VERSION, operation, RERANKER_MODEL, RERANKER_REVISION
        ):
            raise reranking_error("INVALID_RERANKER_OUTPUT", "Reranker returned invalid output.")
        if not isinstance(result.get("runtime_versions"), dict) or not isinstance(result.get("device"), str):
            raise reranking_error("INVALID_RERANKER_OUTPUT", "Reranker returned invalid output.")
        return result

    async def validate_pair_lengths(self, query: str, passages: list[str]) -> None:
        if len(passages) > 20:
            raise reranking_error("INVALID_RERANK_INPUT", "Reranker candidate pool is invalid.", 422)
        try:
            result = await self.client.invoke("validate_rerank_inputs", query, passages)
        except ModalBgeError as exc:
            if exc.code == "MODAL_LOOKUP_FAILED":
                raise reranking_error("RERANKER_NOT_AVAILABLE", "The reranker runtime is unavailable.", 503) from None
            raise reranking_error("RERANKER_NOT_AVAILABLE", "The reranker runtime is unavailable.", 503) from None
        self._validate_result(result, "validate_rerank_inputs")

    async def score(self, query: str, passages: list[str]) -> list[float]:
        if len(passages) > 8:
            raise reranking_error("INVALID_RERANK_INPUT", "Reranker batch is invalid.", 422)
        try:
            result = await self.client.invoke("score_rerank", query, passages)
        except ModalBgeError as exc:
            if exc.code == "MODAL_LOOKUP_FAILED":
                raise reranking_error("RERANKER_NOT_AVAILABLE", "The reranker runtime is unavailable.", 503) from None
            raise reranking_error("RERANKER_INFERENCE_FAILED", "Reranker inference failed.") from None
        result = self._validate_result(result, "score_rerank")
        values = result.get("scores")
        if not isinstance(values, list) or len(values) != len(passages):
            raise reranking_error("INVALID_RERANKER_OUTPUT", "Reranker returned an invalid score count.")
        try:
            scores = [float(value) for value in values]
        except (TypeError, ValueError, OverflowError):
            raise reranking_error("INVALID_RERANKER_OUTPUT", "Reranker returned invalid scores.") from None
        if not all(math.isfinite(value) for value in scores):
            raise reranking_error("INVALID_RERANKER_OUTPUT", "Reranker returned invalid scores.")
        return scores
