"""File storage behind a small interface, so S3/MinIO can replace the local disk later.

Keys are POSIX-style relative paths: `videos/YYYY/MM/<uuid><ext>`,
`evidence/<analysis_uuid>/<step>_<n>.jpg`.
"""

import hashlib
import shutil
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Protocol

from vms.config import get_settings

CHUNK_BYTES = 1024 * 1024


class TooLargeError(Exception):
    pass


class Storage(Protocol):
    def save_stream(
        self, key: str, fileobj: BinaryIO, max_bytes: int | None = None
    ) -> tuple[int, str]:
        """Write the stream to `key`; returns (size, sha256 hex). Raises TooLargeError."""
        ...

    def open(self, key: str) -> BinaryIO: ...

    def path(self, key: str) -> Path:
        """A local filesystem path for `key` (for OpenCV and file responses)."""
        ...

    def delete(self, key: str) -> None: ...

    def exists(self, key: str) -> bool: ...


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def path(self, key: str) -> Path:
        rel = PurePosixPath(key)
        if rel.is_absolute() or ".." in rel.parts or not rel.parts:
            raise ValueError(f"invalid storage key: {key!r}")
        return self.root.joinpath(*rel.parts)

    def save_stream(
        self, key: str, fileobj: BinaryIO, max_bytes: int | None = None
    ) -> tuple[int, str]:
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".part")
        digest = hashlib.sha256()
        size = 0
        try:
            with tmp.open("wb") as out:
                while chunk := fileobj.read(CHUNK_BYTES):
                    size += len(chunk)
                    if max_bytes is not None and size > max_bytes:
                        raise TooLargeError(f"larger than {max_bytes} bytes")
                    digest.update(chunk)
                    out.write(chunk)
            tmp.replace(target)
        finally:
            tmp.unlink(missing_ok=True)
        return size, digest.hexdigest()

    def open(self, key: str) -> BinaryIO:
        return self.path(key).open("rb")

    def delete(self, key: str) -> None:
        target = self.path(key)
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self.path(key).exists()


def get_storage() -> Storage:
    return LocalStorage(get_settings().data_dir)
