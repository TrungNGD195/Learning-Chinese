from pathlib import Path
from shutil import rmtree
from uuid import uuid4

import pytest

from app.ingestion.storage import LocalFileStorage


def test_local_storage_roundtrip_and_atomic_finalization() -> None:
    root = Path(__file__).resolve().parents[2] / "tmp" / f"step52-storage-{uuid4().hex}"
    root.mkdir(parents=True)
    storage = LocalFileStorage(root / "raw")
    discarded_key, discarded = storage.create_temp()
    discarded.close()
    storage.discard(discarded_key)
    assert not (root / "raw" / discarded_key).exists()
    temp_key, handle = storage.create_temp()
    with handle:
        storage.write(handle, b"exact uploaded bytes\x00")
    key = storage.finalize(temp_key, "documents/123/raw.txt")
    with storage.open(key) as raw:
        assert raw.read() == b"exact uploaded bytes\x00"
    assert not (root / "raw" / temp_key).exists()
    rmtree(root)


@pytest.mark.parametrize("key", ["../escape", "documents/../../escape", "C:/outside", "documents\\..\\escape", "/absolute"])
def test_storage_rejects_traversal_and_absolute_keys(key: str) -> None:
    root = Path(__file__).resolve().parents[2] / "tmp" / f"step52-storage-{uuid4().hex}"
    root.mkdir(parents=True)
    storage = LocalFileStorage(root / "raw")
    with pytest.raises(ValueError):
        storage.open(key)
    rmtree(root)


def test_finalized_artifact_cannot_be_overwritten_with_different_bytes() -> None:
    root = Path(__file__).resolve().parents[2] / "tmp" / f"step52-storage-{uuid4().hex}"
    root.mkdir(parents=True)
    storage = LocalFileStorage(root / "raw")
    first_key, first = storage.create_temp()
    with first:
        storage.write(first, b"immutable")
    storage.finalize(first_key, "lessons/1/raw/hash.json")
    second_key, second = storage.create_temp()
    with second:
        storage.write(second, b"different")
    with pytest.raises(FileExistsError):
        storage.finalize(second_key, "lessons/1/raw/hash.json")
    with storage.open("lessons/1/raw/hash.json") as artifact:
        assert artifact.read() == b"immutable"
    storage.delete("lessons/1/raw/hash.json")
    assert not (root / "raw" / "lessons" / "1" / "raw" / "hash.json").exists()
    storage.discard(second_key)
    rmtree(root)
