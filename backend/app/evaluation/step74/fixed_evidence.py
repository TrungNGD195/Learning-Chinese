from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.ai.prompting.evidence import ExternalContextEvidence
from app.ai.reranking.schemas import RerankedCandidate

ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = ROOT / "evaluation/fixtures/lesson_chat_rag/v0.1.0"
EXTERNAL_ROOT = ROOT / "evaluation/fixtures/lesson_chat_rag/trusted_external/v0.1.0"
SCORE_SEMANTICS = "NOT_APPLICABLE_FIXED_EVIDENCE"
ACCEPTED_INTERNAL_HASHES = {
    "manifest.json": "6a02b5c6d43063dcaa381586628cf9b7b3e68945025872039947f02c848b3276",
    "sources/internal-kb-beginner-notes.json": "cef9b36e2f4a426ee49146eccae1f1df503f7494ae791144b5c01e7b1c610c0f",
    "sources/lesson-01-greetings.json": "64bc5a7252d14b28e72ea34934df0411f48584ab2c65b3b2c5eaf049aad6bf3f",
    "sources/lesson-02-numbers-age.json": "765d0ab8c7a05b010fc917538bb690add88622800e58f0aad6b437f052b31a6d",
    "sources/lesson-03-family.json": "797a912041b0f36417eb6c140d5869b1029205e9b3e6987825ca7808dfab94c0",
}


def _digest(value: str | bytes) -> str:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class FixedEvidence:
    evidence_ids: tuple[str, ...]
    requirement_ids: tuple[str, ...]
    source_kind: str
    source_id: str
    stable_locator: str | None
    source_locator: str | None
    title: str
    content: str
    content_sha256: str
    llm_visible_content: str
    candidate: RerankedCandidate | None = None
    external: ExternalContextEvidence | None = None

    def artifact(self) -> dict:
        return {
            "evidence_ids": list(self.evidence_ids),
            "requirement_ids": list(self.requirement_ids),
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "stable_locator": self.stable_locator,
            "source_locator": self.source_locator,
            "title": self.title,
            "content_sha256": self.content_sha256,
            "llm_visible_content": self.llm_visible_content,
        }


class FixedEvidenceResolver:
    """Resolve only accepted, repository-controlled Step 7.2 fixture content."""

    def __init__(self, fixture_root: Path = FIXTURE_ROOT, external_root: Path = EXTERNAL_ROOT):
        manifest_path = fixture_root / "manifest.json"
        self.fixture_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (self.fixture_manifest.get("status") != "ACCEPTED_FOR_EVALUATION_FIXTURE"
                or (self.fixture_manifest.get("source_count"), self.fixture_manifest.get("educational_block_count")) != (4, 26)):
            raise ValueError("Accepted internal fixture pack is required")
        self.fixture_manifest_sha256 = _digest(manifest_path.read_bytes())
        if self.fixture_manifest_sha256 != ACCEPTED_INTERNAL_HASHES["manifest.json"]:
            raise ValueError("Accepted internal fixture manifest hash mismatch")
        aggregate = hashlib.sha256()
        aggregate.update(b"manifest.json\0" + self.fixture_manifest_sha256.encode("ascii") + b"\n")
        self.blocks: dict[str, dict] = {}
        for item in self.fixture_manifest["sources"]:
            raw_source = (fixture_root / item["path"]).read_bytes()
            source_hash = _digest(raw_source)
            if ACCEPTED_INTERNAL_HASHES.get(item["path"]) != source_hash:
                raise ValueError("Accepted internal fixture content hash mismatch")
            aggregate.update(item["path"].encode("utf-8") + b"\0" + source_hash.encode("ascii") + b"\n")
            source = json.loads(raw_source)
            if source.get("source_id") != item["source_id"] or source.get("status") != "ACCEPTED_FOR_EVALUATION_FIXTURE":
                raise ValueError("Fixture source identity/status mismatch")
            for block in source["blocks"]:
                if block["stable_locator"] in self.blocks:
                    raise ValueError("Duplicate fixture stable locator")
                self.blocks[block["stable_locator"]] = {
                    **block,
                    "source_kind": source["source_kind"],
                    "source_title": source.get("lesson_title") or source.get("source_title") or source.get("title"),
                    "lesson_locator": source.get("lesson_locator"),
                    "hsk_level_number": source.get("hsk_level_number"),
                }
        external_path = external_root / "reviewed-sources.json"
        self.external_manifest = json.loads(external_path.read_text(encoding="utf-8"))
        if self.external_manifest.get("status") != "ACCEPTED_FOR_EVALUATION_FIXTURE":
            raise ValueError("Accepted trusted-external fixture registry is required")
        self.external_manifest_sha256 = _digest(external_path.read_bytes())
        if self.external_manifest.get("source_count") != 5:
            raise ValueError("Accepted trusted-external registry source count mismatch")
        self.fixture_content_sha256 = aggregate.hexdigest()
        self.external_by_identity = {
            (row["url"], row["domain"], row["title"]): row
            for row in self.external_manifest["sources"]
            if row.get("review_status") == "ACCEPTED_FOR_EVALUATION_FIXTURE"
        }

    def resolve_case(self, case: dict) -> list[FixedEvidence]:
        merged: dict[tuple[str, str], dict] = {}
        for ref in case["required_evidence"]:
            if ref["source_kind"] == "INTERNAL_CHUNK":
                locator = ref["stable_locator"]
                block = self.blocks.get(locator)
                if block is None:
                    raise ValueError(f"Required stable locator is absent from accepted fixtures: {locator}")
                content = block["content"]
                content_text = "\n".join(
                    f"{key}: {value}" for key, value in content.items() if value is not None
                ) if isinstance(content, dict) else str(content)
                key = ("INTERNAL_CHUNK", locator)
                fixed = merged.setdefault(key, {
                    "source_kind": "INTERNAL_CHUNK", "source_id": block["source_id"],
                    "stable_locator": locator, "source_locator": block["source_locator"],
                    "title": block["source_title"], "content": content_text,
                    "block": block, "evidence_ids": [], "requirement_ids": [],
                })
            elif ref["source_kind"] == "EXTERNAL_URL":
                identity = (ref["url"], ref["domain"], ref.get("title") or "")
                source = self.external_by_identity.get(identity)
                if source is None:
                    raise ValueError("External evidence is absent from accepted reviewed-source registry")
                content_text = "\n".join(source["reviewed_claims"])
                key = ("EXTERNAL_URL", source["source_id"])
                fixed = merged.setdefault(key, {
                    "source_kind": "EXTERNAL_URL", "source_id": source["source_id"],
                    "stable_locator": None, "source_locator": source.get("reviewed_section_title"),
                    "title": source["title"], "content": content_text,
                    "source": source, "evidence_ids": [], "requirement_ids": [],
                })
            else:
                raise ValueError("Unsupported fixed evidence source kind")
            fixed["evidence_ids"].append(ref["evidence_id"])
            if ref.get("requirement_id"):
                fixed["requirement_ids"].append(ref["requirement_id"])

        result = []
        for order, item in enumerate(merged.values(), start=1):
            visible = item["content"]
            candidate = external = None
            if item["source_kind"] == "INTERNAL_CHUNK":
                block = item["block"]
                source_id = item["source_id"]
                chunk_id = uuid5(NAMESPACE_URL, "step74:chunk:" + item["stable_locator"])
                source_uuid = uuid5(NAMESPACE_URL, "step74:source:" + source_id)
                version_uuid = uuid5(NAMESPACE_URL, "step74:version:" + source_id)
                lesson = block["source_kind"] == "LESSON"
                title = item["title"]
                candidate = RerankedCandidate(
                    rank=order, chunk_id=chunk_id, chunk_index=order - 1,
                    content=visible, content_type=block["content_type"],
                    knowledge_version_id=version_uuid, knowledge_source_id=source_uuid,
                    source_type="LESSON" if lesson else "DOCUMENT",
                    source_document_id=None if lesson else source_uuid,
                    source_lesson_id=source_uuid if lesson else None,
                    chunk_lesson_id=source_uuid if lesson else None,
                    document_title=None if lesson else title,
                    lesson_title=title if lesson else None,
                    hsk_level_number=block.get("hsk_level_number"), page_number=None,
                    section=block["content_type"],
                    locator_metadata={"stable_locator": item["stable_locator"],
                                      "source_locator": item["source_locator"],
                                      "fixture_source_id": source_id,
                                      "score_semantics": SCORE_SEMANTICS},
                    distance=0.0, retrieval_score=0.0, rerank_score=0.0, rerank_rank=order,
                )
            else:
                source = item["source"]
                external = ExternalContextEvidence(
                    final_order=order, title=source["title"], url=source["url"],
                    domain=source["domain"], content=visible, rerank_score=0.0,
                )
            result.append(FixedEvidence(
                evidence_ids=tuple(item["evidence_ids"]),
                requirement_ids=tuple(item["requirement_ids"]),
                source_kind=item["source_kind"], source_id=item["source_id"],
                stable_locator=item["stable_locator"], source_locator=item["source_locator"],
                title=item["title"], content=item["content"],
                content_sha256=_digest(item["content"]), llm_visible_content=visible,
                candidate=candidate, external=external,
            ))
        return result

    @staticmethod
    def content_hash(evidence: list[FixedEvidence]) -> str:
        return _digest(_canonical([item.artifact() for item in evidence]))
