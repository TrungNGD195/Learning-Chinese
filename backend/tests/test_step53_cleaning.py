from app.ingestion.cleaning import CLEANING_STRATEGY, CLEANING_VERSION, clean_text


def test_cleaning_is_conservative_deterministic_and_unicode_safe() -> None:
    source = "A\r\n\r\n\r\nCafe\u0301   text\x00\x01\t\n\n\n你好，Xin chào!  "
    expected = "A\n\nCafé  text\n\n你好，Xin chào!"
    assert clean_text(source) == expected
    assert clean_text(source) == clean_text(source)
    assert (CLEANING_STRATEGY, CLEANING_VERSION) == ("basic_text_cleaning", "v1")


def test_cleaning_preserves_code_indentation_and_table_delimiter() -> None:
    assert clean_text("  const  x = 1  \n  next", preserve_spaces=True) == "  const  x = 1  \n  next"
    assert clean_text("left\tright", preserve_spaces=True) == "left\tright"
    assert clean_text("  meaningful leading space  ") == "  meaningful leading space"
