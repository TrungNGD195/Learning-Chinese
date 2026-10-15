from __future__ import annotations

import math
from importlib.metadata import version

import modal

from app.ai.modal_bge.schemas import (
    CONTRACT_VERSION, EMBEDDING_MODEL, EMBEDDING_REVISION,
    RERANKER_MODEL, RERANKER_REVISION, failure, success,
)

APP_NAME = "trung-chinese-bge-validation"
CLASS_NAME = "BgeInference"
VOLUME_NAME = "trung-chinese-bge-model-cache"
CACHE_PATH = "/root/.cache/huggingface"

base_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch==2.14.1", "sentence-transformers==6.1.0", "transformers==5.18.0",
    )
)
image = base_image.env({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"})
model_cache = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
app = modal.App(APP_NAME)


@app.function(image=base_image, volumes={CACHE_PATH: model_cache}, retries=0)
def populate_model_cache() -> dict:
    """Stage exact snapshots when Stage B is separately authorized; never called in Stage A."""
    from sentence_transformers import SentenceTransformer
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    SentenceTransformer(EMBEDDING_MODEL, revision=EMBEDDING_REVISION, device="cpu")
    AutoTokenizer.from_pretrained(RERANKER_MODEL, revision=RERANKER_REVISION)
    AutoModelForSequenceClassification.from_pretrained(RERANKER_MODEL, revision=RERANKER_REVISION)
    model_cache.commit()
    return {"embedding_revision": EMBEDDING_REVISION, "reranker_revision": RERANKER_REVISION}


@app.cls(
    image=image,
    gpu="T4",
    volumes={CACHE_PATH: model_cache},
    min_containers=0,
    max_containers=2,
    retries=0,
)
class BgeInference:
    """Inference only: no DB, retrieval, RAG, citations, or application state."""

    @modal.enter()
    def load_models(self) -> None:
        import torch
        from sentence_transformers import SentenceTransformer
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.torch = torch
        self.embedding = SentenceTransformer(
            EMBEDDING_MODEL, revision=EMBEDDING_REVISION, device="cuda"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(RERANKER_MODEL, revision=RERANKER_REVISION)
        self.reranker = AutoModelForSequenceClassification.from_pretrained(
            RERANKER_MODEL, revision=RERANKER_REVISION
        ).to("cuda").eval()

    @modal.method()
    def runtime_info(self) -> dict:
        self.torch.cuda.synchronize()
        return {
            "contract_version": CONTRACT_VERSION,
            "embedding_model_name": EMBEDDING_MODEL,
            "embedding_model_revision": EMBEDDING_REVISION,
            "reranker_model_name": RERANKER_MODEL,
            "reranker_model_revision": RERANKER_REVISION,
            "device": str(self.reranker.device),
            "gpu_name": self.torch.cuda.get_device_name(0),
            "gpu_total_vram_bytes": int(self.torch.cuda.get_device_properties(0).total_memory),
            "torch_version": version("torch"),
            "cuda_version": self.torch.version.cuda,
            "runtime_versions": {
                name: version(name) for name in ("sentence-transformers", "transformers", "torch")
            },
            "vram_allocated_bytes": int(self.torch.cuda.memory_allocated()),
            "vram_reserved_bytes": int(self.torch.cuda.memory_reserved()),
            "vram_max_allocated_bytes": int(self.torch.cuda.max_memory_allocated()),
            "vram_max_reserved_bytes": int(self.torch.cuda.max_memory_reserved()),
        }

    @modal.method()
    def embed_query(self, text: str) -> dict:
        return self._embed([text], "embed_query", single=True)

    @modal.method()
    def embed_documents(self, texts: list[str], *, batch_size: int) -> dict:
        if not texts or batch_size <= 0:
            return failure("INVALID_EMBEDDING_OUTPUT", "Embedding input is invalid.")
        return self._embed(texts, "embed_documents", batch_size=batch_size)

    def _embed(self, texts: list[str], operation: str, *, single: bool = False, batch_size: int = 32) -> dict:
        encoded = self.embedding.tokenizer(texts, add_special_tokens=True, truncation=False)
        if any(len(ids) > int(self.embedding.max_seq_length) for ids in encoded["input_ids"]):
            return failure("EMBEDDING_INPUT_TOO_LONG", "Embedding input exceeds the model token limit.")
        vectors = self.embedding.encode(
            texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False,
        )
        values = [[float(value) for value in vector] for vector in vectors]
        invalid = any(
            len(vector) != 1024 or not all(math.isfinite(x) for x in vector)
            or abs(math.sqrt(sum(x * x for x in vector)) - 1.0) > 1e-3
            for vector in values
        )
        if invalid:
            return failure("INVALID_EMBEDDING_OUTPUT", "Embedding output is invalid.")
        metadata = self._metadata(operation, EMBEDDING_MODEL, EMBEDDING_REVISION)
        metadata["vector" if single else "vectors"] = values[0] if single else values
        return metadata

    @modal.method()
    def validate_rerank_inputs(self, query: str, passages: list[str]) -> dict:
        max_length = min(
            int(self.reranker.config.max_position_embeddings),
            int(self.tokenizer.model_max_length),
        )
        for passage in passages:
            tokens = self.tokenizer(query, passage, add_special_tokens=True, truncation=False)
            ids = tokens["input_ids"]
            if ids and isinstance(ids[0], list):
                ids = ids[0]
            if len(ids) > max_length:
                return failure("RERANK_INPUT_TOO_LONG", "A query and passage exceed the reranker input limit.")
        return self._metadata("validate_rerank_inputs", RERANKER_MODEL, RERANKER_REVISION)

    @modal.method()
    def score_rerank(self, query: str, passages: list[str]) -> dict:
        if len(passages) > 8:
            return failure("INVALID_RERANKER_OUTPUT", "Reranker batch is invalid.")
        if not passages:
            result = self._metadata("score_rerank", RERANKER_MODEL, RERANKER_REVISION)
            result["scores"] = []
            return result
        tokens = self.tokenizer(
            [query] * len(passages), passages, add_special_tokens=True,
            padding=True, truncation=False, return_tensors="pt",
        )
        tokens = {key: value.to("cuda") for key, value in tokens.items()}
        with self.torch.inference_mode():
            logits = self.reranker(**tokens).logits.reshape(-1)
        scores = [float(value) for value in logits.detach().cpu().tolist()]
        if len(scores) != len(passages) or not all(math.isfinite(x) for x in scores):
            return failure("INVALID_RERANKER_OUTPUT", "Reranker inference failed.")
        result = self._metadata("score_rerank", RERANKER_MODEL, RERANKER_REVISION)
        result["scores"] = scores
        return result

    @staticmethod
    def _metadata(operation: str, model_name: str, model_revision: str) -> dict:
        return success(
            operation, model_name, model_revision,
            runtime_versions={name: version(name) for name in ("sentence-transformers", "transformers", "torch")},
            device="cuda",
        )
