"""Configuration and resource limits (Requirements R1.2, R1.5, R8)."""
from __future__ import annotations

import os

# File size cap (bytes). Default 25 MB; override via env.
MAX_FILE_BYTES = int(os.environ.get("PRIVACYFORGE_MAX_FILE_BYTES", 25 * 1024 * 1024))

# Max rows/cells to guard against runaway memory.
MAX_ROWS = int(os.environ.get("PRIVACYFORGE_MAX_ROWS", 500_000))
MAX_COLS = int(os.environ.get("PRIVACYFORGE_MAX_COLS", 2_000))

# Decompression-bomb guard: refuse archives/workbooks whose declared
# uncompressed size exceeds this multiple of the compressed size.
MAX_DECOMPRESS_RATIO = int(os.environ.get("PRIVACYFORGE_MAX_DECOMPRESS_RATIO", 100))

# Master key for the vault. If unset, vault operations refuse (no default key).
MASTER_KEY_ENV = "PRIVACYFORGE_MASTER_KEY"
