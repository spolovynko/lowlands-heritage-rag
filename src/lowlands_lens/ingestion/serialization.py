"""Deterministic serialization, compression, and hashing primitives."""

import gzip
import hashlib
import json
from collections.abc import Mapping


def canonical_json_bytes(document: Mapping[str, object]) -> bytes:
    """Serialize source-shaped JSON deterministically without a trailing newline."""
    return json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def deterministic_gzip(content: bytes) -> bytes:
    """Compress bytes with a reproducible header and fixed compression level."""
    return gzip.compress(content, compresslevel=9, mtime=0)


class Sha256Hasher:
    """Production SHA-256 content hasher."""

    def hexdigest(self, content: bytes) -> str:
        """Return a lowercase SHA-256 hexadecimal digest."""
        return hashlib.sha256(content).hexdigest()
