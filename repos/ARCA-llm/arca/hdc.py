"""Hyperdimensional computing layer.

Binary hypervectors (D=10.000 bits) encode words as bundles of their
character trigrams, so typo'd or accented variants share most of their
trigrams and land near the same point in hyperspace. Sentences bundle
their word vectors with positional rotation. Similarity is normalized
Hamming agreement: random pairs sit near 0.5, related text climbs above
0.6, near-duplicates approach 1.0. No training, no gradients — pure
algebra over fixed random bases derived deterministically from content.
"""
from __future__ import annotations

import hashlib
import re

import numpy as np

D = 10_000
_TOKEN = re.compile(r"[^\wáéíóúñü]+", re.UNICODE)
_word_cache: dict[str, np.ndarray] = {}
_WORD_CACHE_MAX = 50_000


def _stable_seed(text: str) -> int:
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def _base_vector(token: str) -> np.ndarray:
    rng = np.random.Generator(np.random.PCG64(_stable_seed(token)))
    return rng.integers(0, 2, size=D, dtype=bool)


def _bundle(vectors: list[np.ndarray]) -> np.ndarray:
    if not vectors:
        return np.zeros(D, dtype=bool)
    total = np.zeros(D, dtype=np.int32)
    for vector in vectors:
        total += vector.astype(np.int32) * 2 - 1
    return total > 0


def word_hv(word: str) -> np.ndarray:
    cached = _word_cache.get(word)
    if cached is not None:
        return cached
    padded = f"⟨{word.lower()}⟩"
    trigrams = [padded[i : i + 3] for i in range(len(padded) - 2)]
    vector = _bundle([_base_vector(trigram) for trigram in trigrams])
    if len(_word_cache) >= _WORD_CACHE_MAX:
        _word_cache.clear()
    _word_cache[word] = vector
    return vector


def tokenize(text: str) -> list[str]:
    return [token for token in _TOKEN.split(text) if len(token) > 1]


def encode(text: str) -> np.ndarray:
    """Sentence/phrase vector with cheap positional structure."""
    words = [word for word in tokenize(text)][:64]
    if not words:
        return np.zeros(D, dtype=bool)
    rotated = [np.roll(word_hv(word), shift=index % 7) for index, word in enumerate(words)]
    return _bundle(rotated)


def similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Normalized Hamming agreement in [0,1]; unrelated ≈ 0.5."""
    if a.size == 0 or b.size == 0:
        return 0.0
    return float(1.0 - np.count_nonzero(a ^ b) / D)


RELATED = 0.62
STRONG = 0.72
