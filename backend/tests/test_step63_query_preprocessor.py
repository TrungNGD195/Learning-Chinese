import unicodedata

import pytest

from app.ai.retrieval.query_preprocessor import QueryPreprocessor
from app.core.errors import ApplicationError


def test_query_preprocessor_trims_and_collapses_unicode_whitespace():
    assert QueryPreprocessor.preprocess("  hello\t\nworld  ") == "hello world"


def test_query_preprocessor_applies_unicode_nfc():
    decomposed = "a\u0308"
    assert QueryPreprocessor.preprocess(decomposed) == unicodedata.normalize("NFC", decomposed)


def test_query_preprocessor_is_stable_for_normal_text():
    query = "怎么使用 了？"
    assert QueryPreprocessor.preprocess(QueryPreprocessor.preprocess(query)) == query


@pytest.mark.parametrize("query", ["", " \t\n ", "\u00a0\u3000"])
def test_query_preprocessor_rejects_whitespace_only(query: str):
    with pytest.raises(ApplicationError) as error:
        QueryPreprocessor.preprocess(query)
    assert error.value.code == "EMPTY_RETRIEVAL_QUERY"
    assert error.value.status_code == 422


def test_query_preprocessor_does_not_rewrite_query_text():
    assert QueryPreprocessor.preprocess("x y") == "x y"
