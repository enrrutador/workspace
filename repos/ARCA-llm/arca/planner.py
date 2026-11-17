"""Generation as planning, not prediction.

Given an intent, ARCA fills discourse SLOTS (definition → types → uses …)
with REAL sentences mined from its evidence graph. A bounded A* search picks
the next sentence minimizing (1 - relevance) + HDC-redundancy against already
chosen sentences + slot-order penalties. Every emitted sentence is traceable
to a source passage; connectors make the stitch read like natural prose."""
from __future__ import annotations

import heapq
import re
import unicodedata
from typing import Any

from arca import hdc


def _strip_accents(text: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFD", text) if unicodedata.category(char) != "Mn")

CONNECTORS = {
    "definicion": "",
    "tipo": "Entre sus variantes, ",
    "uso": "Además, ",
    "mecanismo": "En cuanto a su funcionamiento, ",
    "historia": "En su origen, ",
    "dato": "Cabe destacar que ",
}

SLOTS = {
    "que_es": ["definicion", "tipo", "uso"],
    "como_funciona": ["mecanismo", "uso", "dato"],
    "historia": ["historia", "dato"],
}

_MAX_SENTENCES = 4


def _clean(sentence: str) -> str:
    cleaned = re.sub(r"\[\s*\d+\s*\]", "", sentence)
    cleaned = cleaned.replace("[ editar ]", "").replace("[ editar]", "")
    return " ".join(cleaned.split()).strip()


def _with_connector(slot: str, text: str, first: bool) -> str:
    connector = "" if first else CONNECTORS.get(slot, "")
    if not connector:
        return text
    return f"{connector}{text[0].lower()}{text[1:]}" if text[:1].isupper() and not text[:2].isupper() else f"{connector}{text}"


def plan_answer(intent: str, subject: str, candidates: list[dict[str, Any]], covered_aspects: list[str] | None = None, max_sentences: int = _MAX_SENTENCES) -> tuple[str, list[str], list[str]]:
    """Returns (prose, used_urls, aspects_covered). Deterministic bounded search."""
    slots = [slot for slot in SLOTS.get(intent, SLOTS["que_es"]) if slot not in (covered_aspects or [])]
    if not slots:
        slots = ["dato"]
    subject_tokens = {token.casefold() for token in hdc.tokenize(subject)}

    pool: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for candidate in candidates:
        text = _clean(str(candidate.get("passage") or candidate.get("content") or ""))
        if len(text) < 40 or text[-1] not in ".!?…:":
            continue
        key = _strip_accents(text)[:50].casefold()
        if key in seen_keys:
            continue
        seen_keys.add(key)
        tokens = {token.casefold() for token in hdc.tokenize(text)}
        relevance = len(subject_tokens & tokens) / max(len(subject_tokens), 1)
        pool.append({
            "text": text,
            "aspect": str(candidate.get("aspect") or "dato"),
            "url": str(candidate.get("source_url") or candidate.get("url") or ""),
            "score": float(candidate.get("score") or 0.5),
            "relevance": relevance,
            "hv": hdc.encode(text),
        })
    if not pool:
        return "", [], []

    def step_cost(item: dict[str, Any], chosen_hvs: list[np.ndarray]) -> float:
        redundancy = max((hdc.similarity(item["hv"], hv) for hv in chosen_hvs), default=0.0) - 0.5
        return (1.0 - min(max(item["score"], item["relevance"]), 1.0)) * 0.7 + max(redundancy, 0.0) * 0.9

    counter = 0
    start = (0.0, counter, frozenset(), -1, ())
    heap: list[tuple[float, int, float, int, tuple]] = [(0.0, 0, 0.0, -1, ())]
    best_goal: list[dict[str, Any]] | None = None
    expansions = 0
    while heap and expansions < 300:
        _, _, cost, last_index, chosen = heapq.heappop(heap)
        expansions += 1
        covered = {item["aspect"] for item in chosen}
        missing = [slot for slot in slots if slot not in covered]
        if not missing or len(chosen) >= max_sentences:
            best_goal = list(chosen)
            break
        chosen_hvs = [item["hv"] for item in chosen]
        for index, item in enumerate(pool):
            if index == last_index or item["aspect"] in covered:
                continue
            new_cost = cost + step_cost(item, chosen_hvs)
            heuristic = 0.04 * (len(missing) - 1)
            counter += 1
            heapq.heappush(heap, (new_cost + heuristic, counter, new_cost, index, chosen + (item,)))
    if best_goal is None:
        return "", [], []

    parts: list[str] = []
    urls: list[str] = []
    aspects: list[str] = []
    for position, item in enumerate(best_goal):
        parts.append(_with_connector(item["aspect"], item["text"], position == 0))
        aspects.append(item["aspect"])
        if item["url"] and item["url"] not in urls:
            urls.append(item["url"])
    return " ".join(parts), urls[:3], aspects
