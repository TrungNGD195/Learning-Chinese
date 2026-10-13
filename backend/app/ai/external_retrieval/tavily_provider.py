from __future__ import annotations

import logging
from time import perf_counter
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.ai.external_retrieval.errors import (
    EXTERNAL_RETRIEVAL_AUTH_FAILED,
    EXTERNAL_RETRIEVAL_FAILED,
    EXTERNAL_RETRIEVAL_NOT_CONFIGURED,
    EXTERNAL_RETRIEVAL_TIMEOUT,
    external_retrieval_error,
)
from app.ai.external_retrieval.schemas import ExternalCandidate
from app.core.config import Settings

logger = logging.getLogger("app.ai.external_retrieval")


class TavilyExternalRetrievalProvider:
    def __init__(self, settings: Settings, *, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.client = client

    async def search(self, query: str, limit: int) -> tuple[ExternalCandidate, ...]:
        started = perf_counter()
        key = self.settings.external_retrieval_api_key
        if key is None or not key.get_secret_value().strip():
            raise external_retrieval_error(EXTERNAL_RETRIEVAL_NOT_CONFIGURED)
        if limit != 10:
            raise external_retrieval_error(EXTERNAL_RETRIEVAL_FAILED)
        body = {
            "query": query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": 10,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "include_image_descriptions": False,
            "include_favicon": False,
            "include_domains": list(self.settings.external_retrieval_allowed_domains),
            "auto_parameters": False,
        }
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=self.settings.external_retrieval_request_timeout_seconds)
        status = "FAILED"
        error_code = EXTERNAL_RETRIEVAL_FAILED
        try:
            response = await client.post(
                f"{self.settings.external_retrieval_base_url}/search",
                headers={"Authorization": f"Bearer {key.get_secret_value()}", "Content-Type": "application/json"},
                json=body,
            )
            if response.status_code == 401:
                error_code = EXTERNAL_RETRIEVAL_AUTH_FAILED
                raise external_retrieval_error(error_code)
            if response.status_code < 200 or response.status_code >= 300:
                raise external_retrieval_error(EXTERNAL_RETRIEVAL_FAILED)
            try:
                payload: Any = response.json()
            except Exception:
                raise external_retrieval_error(EXTERNAL_RETRIEVAL_FAILED) from None
            rows = payload.get("results") if isinstance(payload, dict) else None
            if not isinstance(rows, list):
                raise external_retrieval_error(EXTERNAL_RETRIEVAL_FAILED)
            candidates = []
            for rank, row in enumerate(rows, start=1):
                if not isinstance(row, dict):
                    raise external_retrieval_error(EXTERNAL_RETRIEVAL_FAILED)
                title, url, content = row.get("title"), row.get("url"), row.get("content")
                if not all(isinstance(v, str) and v.strip() for v in (title, url, content)):
                    raise external_retrieval_error(EXTERNAL_RETRIEVAL_FAILED)
                score = row.get("score")
                try:
                    score = float(score) if score is not None else None
                except (TypeError, ValueError, OverflowError):
                    score = None
                if score is not None and (score != score or score in {float("inf"), float("-inf")}):
                    score = None
                # The provider domain label is deliberately ignored; derive the candidate host from its URL.
                try:
                    domain = (urlsplit(url).hostname or "invalid-host").lower().removesuffix(".")
                except ValueError:
                    raise external_retrieval_error(EXTERNAL_RETRIEVAL_FAILED) from None
                candidates.append(ExternalCandidate(title, url, domain, content, rank, score))
            status, error_code = "SUCCEEDED", None
            return tuple(candidates[:10])
        except httpx.TimeoutException:
            error_code = EXTERNAL_RETRIEVAL_TIMEOUT
            raise external_retrieval_error(error_code) from None
        except httpx.HTTPError:
            error_code = EXTERNAL_RETRIEVAL_FAILED
            raise external_retrieval_error(error_code) from None
        finally:
            if owns_client:
                await client.aclose()
            logger.info("external_retrieval_provider", extra={
                "external_provider": "tavily", "external_requested_count": 10,
                "external_returned_count": len(candidates) if status == "SUCCEEDED" else 0,
                "external_duration_ms": round((perf_counter() - started) * 1000, 2),
                "status": status, "error_stage": "PROVIDER", "error_code": error_code,
            })
