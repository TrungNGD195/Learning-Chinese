import os
import itertools
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import uuid4

from app.ingestion.schemas import validate_storage_key


class FileStorage(Protocol):
    def create_temp(self) -> tuple[str, BinaryIO]: ...
    def write(self, handle: BinaryIO, data: bytes) -> None: ...
    def finalize(self, temp_key: str, storage_key: str) -> str: ...
    def discard(self, temp_key: str) -> None: ...
    def delete(self, storage_key: str) -> None: ...
    def open(self, storage_key: str) -> BinaryIO: ...
    def open_temp(self, temp_key: str) -> BinaryIO: ...


class LocalFileStorage:
    """Private local immutable artifact storage rooted at a configured directory."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser().resolve()
        self.temp_root = self.root / "tmp"
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        key = validate_storage_key(key)
        candidate = (self.root / Path(*key.split("/"))).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("Storage key escapes configured root") from exc
        return candidate

    def create_temp(self) -> tuple[str, BinaryIO]:
        key = f"tmp/{uuid4().hex}.part"
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        return key, path.open("xb")

    def write(self, handle: BinaryIO, data: bytes) -> None:
        handle.write(data)

    def finalize(self, temp_key: str, storage_key: str) -> str:
        source = self._path(temp_key)
        destination = self._path(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            # Hash-keyed Lesson objects can be reused only when the immutable
            # existing artifact is byte-for-byte identical to this source.
            with source.open("rb") as left, destination.open("rb") as right:
                same = all(a == b for a, b in itertools.zip_longest(
                    iter(lambda: left.read(64 * 1024), b""),
                    iter(lambda: right.read(64 * 1024), b""),
                    fillvalue=None,
                ))
            if not same:
                raise FileExistsError("Immutable storage key already exists")
            source.unlink()
            return storage_key
        os.replace(source, destination)
        return storage_key

    def discard(self, temp_key: str) -> None:
        self._path(temp_key).unlink(missing_ok=True)

    def delete(self, storage_key: str) -> None:
        self._path(storage_key).unlink(missing_ok=True)

    def open(self, storage_key: str) -> BinaryIO:
        return self._path(storage_key).open("rb")

    def open_temp(self, temp_key: str) -> BinaryIO:
        if not temp_key.startswith("tmp/"):
            raise ValueError("Invalid temporary storage key")
        return self._path(temp_key).open("rb")

    def write_bytes(self, key: str, data: bytes) -> None:
        temp_key, handle = self.create_temp()
        try:
            with handle:
                handle.write(data)
            self.finalize(temp_key, key)
        except Exception:
            self.discard(temp_key)
            raise
