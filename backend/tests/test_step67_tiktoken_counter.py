from app.ai.prompting.token_counter import TiktokenTokenCounter, TokenCounter


def test_tiktoken_counter_uses_local_o200k_vocab_for_chinese_and_vietnamese() -> None:
    counter = TiktokenTokenCounter()
    assert counter._encoding.name == "o200k_base"
    assert counter.count("你好，世界") == 3
    assert counter.count("Xin chào, tôi đang học tiếng Trung.") == 10
    assert counter.count("你好，世界") == counter.count("你好，世界")


def test_tiktoken_counter_rejects_non_text() -> None:
    try:
        TiktokenTokenCounter().count(None)  # type: ignore[arg-type]
    except TypeError:
        return
    raise AssertionError("non-text token input should fail")
