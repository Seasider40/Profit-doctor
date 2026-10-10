"""Durable content-addressed receipt bytes, never a source-authentication claim."""
import hashlib
import os
from pathlib import Path
import re
import tempfile


class EvidenceStore:
    LIMIT = 50 * 1024 * 1024

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, digest):
        if not re.fullmatch('[a-f0-9]{64}', digest):
            raise ValueError('Invalid storage identity')
        path = self.root / digest
        if path.is_symlink():
            raise ValueError('Linked evidence objects refused')
        return path

    @staticmethod
    def filename(value):
        if (not value or len(value) > 255 or value in ('.', '..') or
                any(c in value for c in '/\\:\x00') or any(ord(c) < 32 for c in value)):
            raise ValueError('Unsafe original filename')
        return value

    def put(self, data):
        if not isinstance(data, bytes) or not 0 < len(data) <= self.LIMIT:
            raise ValueError('Receipt must contain 1 byte to 50 MiB')
        digest = hashlib.sha256(data).hexdigest()
        target = self.path(digest)
        if target.exists():
            self.read(digest, len(data))
            return digest
        name = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.root, prefix='.pending-', delete=False) as stream:
                name = stream.name
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, target)
            return digest
        finally:
            if name and Path(name).exists():
                Path(name).unlink()

    def read(self, digest, size):
        data = self.path(digest).read_bytes()
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Stored evidence integrity mismatch')
        return data

    def unreferenced(self, referenced):
        return sorted(p.name for p in self.root.iterdir() if p.is_file() and
                      re.fullmatch('[a-f0-9]{64}', p.name) and p.name not in referenced)
