import pytest

from app.ai.citations.errors import CITATION_FORMAT_INVALID
from app.ai.citations.parser import parse_citations
from app.core.errors import ApplicationError


@pytest.mark.parametrize("text", ["[S1]", "[S12]", "a [S1][S3]"])
def test_plain_text_citation_tokens_are_parsed(text):
    parsed = parse_citations(text)
    assert parsed.occurrence_count == len(parsed.occurrences)
    assert all(text[item.start:item.end] == f"[{item.label}]" for item in parsed.occurrences)


@pytest.mark.parametrize("text", ["[ S1 ]", "[S1,S2]", "[SX]", "[S0]", "[^1]", "unclosed [S1"])
def test_malformed_eligible_tokens_fail(text):
    with pytest.raises(ApplicationError) as error:
        parse_citations(text)
    assert error.value.code == CITATION_FORMAT_INVALID


def test_non_citations_code_fences_inline_code_and_link_labels_are_excluded():
    text = "S1 (1) `[S2]`\n```text\n[S3]\n```\n[S4](https://private.example)"
    assert parse_citations(text).occurrences == ()


def test_only_plain_text_occurrences_count_and_offsets_use_original_text():
    text = "Rule [S1] then `[S2]` and [S3](https://hidden.invalid)"
    parsed = parse_citations(text)
    assert [(item.label, text[item.start:item.end]) for item in parsed.occurrences] == [("S1", "[S1]")]


def test_fenced_and_inline_only_markers_are_not_reported_as_occurrences():
    assert parse_citations("~~~md\n[S1]\n~~~").occurrence_count == 0
    assert parse_citations("`[S1]`").occurrence_count == 0


@pytest.mark.parametrize("text", ["[1]", "[12]", "[2026]"])
def test_numeric_bracket_text_is_not_citation_like(text):
    parsed = parse_citations(text)
    assert parsed.occurrence_count == 0
    assert parsed.occurrences == ()
