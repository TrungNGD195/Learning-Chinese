from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any

from app.ai.reranking.errors import reranking_error
from app.ai.reranking.schemas import RerankerProviderIdentity
from app.core.config import Settings


class TransformersRerankerProvider:
    """Lazy local BGE cross-encoder using the locked Transformers/PyTorch stack."""

    def __init__(self, settings: Settings, *, loader=None, torch_module=None):
        self.settings = settings
        self._loader = loader
        self._torch = torch_module
        self._tokenizer = None
        self._model = None
        try:
            transformers_version = version("transformers")
            torch_version = version("torch")
        except PackageNotFoundError as exc:
            raise reranking_error(
                "RERANKER_NOT_AVAILABLE", "The local reranker runtime is unavailable.", 503
            ) from exc
        self.identity = RerankerProviderIdentity(
            provider="LOCAL",
            provider_version=f"transformers/{transformers_version};torch/{torch_version}",
            model_name=settings.reranker_model_name,
            model_revision=settings.reranker_model_revision,
            reranker_input_version=settings.reranker_input_version,
        )
        self._resolved_device: str | None = None

    @property
    def device(self) -> str:
        if self._resolved_device is not None:
            return self._resolved_device
        torch = self._load_torch()
        requested = self.settings.reranker_device
        if requested == "auto":
            if torch.cuda.is_available():
                return "cuda"
            mps = getattr(getattr(torch, "backends", None), "mps", None)
            if mps is not None and mps.is_available():
                return "mps"
            return "cpu"
        if requested == "cuda" and not torch.cuda.is_available():
            raise reranking_error("RERANKER_NOT_AVAILABLE", "The configured reranker device is unavailable.", 503)
        if requested == "mps":
            mps = getattr(getattr(torch, "backends", None), "mps", None)
            if mps is None or not mps.is_available():
                raise reranking_error("RERANKER_NOT_AVAILABLE", "The configured reranker device is unavailable.", 503)
        return requested

    def _load_torch(self):
        if self._torch is None:
            try:
                import torch
            except Exception as exc:
                raise reranking_error(
                    "RERANKER_NOT_AVAILABLE", "The local reranker runtime is unavailable.", 503
                ) from exc
            self._torch = torch
        return self._torch

    def _load_model(self) -> tuple[Any, Any]:
        if self._model is not None and self._tokenizer is not None:
            return self._tokenizer, self._model
        try:
            if self._loader is None:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer

                tokenizer_loader = AutoTokenizer
                model_loader = AutoModelForSequenceClassification
            else:
                tokenizer_loader, model_loader = self._loader
            revision = self.settings.reranker_model_revision
            tokenizer = tokenizer_loader.from_pretrained(
                self.settings.reranker_model_name,
                revision=revision,
            )
            model = model_loader.from_pretrained(
                self.settings.reranker_model_name,
                revision=revision,
            )
            device = self.device
            model.to(device)
            model.eval()
            self._tokenizer, self._model = tokenizer, model
            self._resolved_device = str(getattr(model, "device", device))
            return tokenizer, model
        except Exception as exc:
            if getattr(exc, "code", None) == "RERANKER_NOT_AVAILABLE":
                raise
            raise reranking_error(
                "RERANKER_NOT_AVAILABLE", "The local reranker model could not be loaded.", 503
            ) from None

    @staticmethod
    def _pair_length(tokenizer, query: str, passage: str) -> int:
        tokens = tokenizer(
            query,
            passage,
            add_special_tokens=True,
            truncation=False,
        )
        input_ids = tokens["input_ids"]
        if input_ids and isinstance(input_ids[0], list):
            if len(input_ids) != 1:
                raise ValueError("unexpected tokenizer batch shape")
            input_ids = input_ids[0]
        return len(input_ids)

    def _max_pair_length(self, tokenizer, model) -> int:
        model_limit = getattr(getattr(model, "config", None), "max_position_embeddings", None)
        tokenizer_limit = getattr(tokenizer, "model_max_length", None)
        limits = [
            int(value)
            for value in (model_limit, tokenizer_limit)
            if isinstance(value, int) and 0 < value < 1_000_000
        ]
        if not limits:
            raise reranking_error(
                "RERANKER_NOT_AVAILABLE", "The reranker input limit is unavailable.", 503
            )
        return min(limits)

    async def validate_pair_lengths(self, query: str, passages: list[str]) -> None:
        try:
            tokenizer, model = self._load_model()
            max_length = self._max_pair_length(tokenizer, model)
            for passage in passages:
                if self._pair_length(tokenizer, query, passage) > max_length:
                    raise reranking_error(
                        "RERANK_INPUT_TOO_LONG", "A query and passage exceed the reranker input limit.", 422
                    )
        except Exception as exc:
            if getattr(exc, "code", None) in {"RERANK_INPUT_TOO_LONG", "RERANKER_NOT_AVAILABLE"}:
                raise
            raise reranking_error(
                "RERANKER_NOT_AVAILABLE", "Reranker input could not be validated.", 503
            ) from None

    async def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        try:
            tokenizer, model = self._load_model()
            torch = self._load_torch()
            encoded = tokenizer(
                [query] * len(passages),
                passages,
                add_special_tokens=True,
                padding=True,
                truncation=False,
                return_tensors="pt",
            )
            encoded = {key: value.to(self.device) for key, value in encoded.items()}
            with torch.inference_mode():
                output = model(**encoded)
            logits = output.logits.reshape(-1)
            if int(logits.numel()) != len(passages):
                raise reranking_error(
                    "INVALID_RERANKER_OUTPUT", "Reranker returned an invalid score count."
                )
            return [float(value) for value in logits.detach().cpu().tolist()]
        except Exception as exc:
            if getattr(exc, "code", None) == "INVALID_RERANKER_OUTPUT":
                raise
            raise reranking_error(
                "RERANKER_INFERENCE_FAILED", "Local reranker inference failed."
            ) from None
