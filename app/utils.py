"""Utility helpers for chunking and hashing."""

from __future__ import annotations

import hashlib


def chunk_material(content: str) -> list[str]:
    """Split content into simple paragraph-based chunks."""
    chunks = [c.strip() for c in content.split("\n\n") if c.strip()]
    return chunks


def card_hash(front: str, back: str) -> str:
    """Return SHA256 hash for front/back pair."""
    return hashlib.sha256((front + "\x1e" + back).encode("utf-8")).hexdigest()
