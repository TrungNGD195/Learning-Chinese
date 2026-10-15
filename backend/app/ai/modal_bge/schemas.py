from __future__ import annotations

from typing import Any

CONTRACT_VERSION = "modal-bge-runtime/v1"
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
RERANKER_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"


def success(operation: str, model_name: str, model_revision: str, **values: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "contract_version": CONTRACT_VERSION,
        "operation": operation,
        "model_name": model_name,
        "model_revision": model_revision,
        **values,
    }


def failure(error_code: str, safe_message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "contract_version": CONTRACT_VERSION,
        "error_code": error_code,
        "safe_message": safe_message,
    }
