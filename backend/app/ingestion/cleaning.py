import re
import unicodedata


CLEANING_STRATEGY = "basic_text_cleaning"
CLEANING_VERSION = "v1"
_BLANK_LINES = re.compile(r"\n{3,}")
_ASCII_SPACES = re.compile(r" {3,}")


def clean_text(text: str, *, preserve_spaces: bool = False) -> str:
    """Apply the frozen technical cleanup; remove C0/C1 controls except tab/LF."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text).replace("\x00", "")
    text = "".join(
        char for char in text
        if char in "\t\n" or not (unicodedata.category(char) == "Cc")
    )
    if not preserve_spaces:
        text = "\n".join(line.rstrip() for line in text.split("\n"))
    if not preserve_spaces:
        text = _ASCII_SPACES.sub("  ", text)
        text = _BLANK_LINES.sub("\n\n", text)
    return text if preserve_spaces else text.rstrip()
