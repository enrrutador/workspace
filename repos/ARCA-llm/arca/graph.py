"""Evidence graph: concepts, typed triples and aspect-tagged passages mined
from everything ARCA reads. Stored in the same portable SQLite file; grows
with browsing up to a configurable cap. No training — mining is deterministic
Spanish relational patterns over real sentences."""
from __future__ import annotations

import re
from typing import Any

import numpy as np

from arca import hdc
from arca.memory.store import MemoryStore

_PATTERNS = [
    (re.compile(r"(?P<subj>[A-ZÁÉÍÓÚÑ][\wáéíóúñ]+(?:\s+[\wáéíóúñ]+){0,3})\s+es\s+(?:un|una|el|la|todo|toda)\s+(?P<obj>[^.;]{3,140})", re.I), "es_un", "definicion"),
    (re.compile(r"(?P<subj>[\wáéíóúñ]{3,30})\s+(?:se utiliza|se usa|sirve para|sirven para|permiten?)\s+(?:para\s+)?(?P<obj>[^.;]{5,140})", re.I), "se_usa_para", "uso"),
    (re.compile(r"(?P<subj>[\wáéíóúñ]{3,30})\s+(?:funciona|operan?)\s+(?:mediante|con|a través de|gracias a)\s+(?P<obj>[^.;]{5,140})", re.I), "funciona_mediante", "mecanismo"),
    (re.compile(r"\bfue\s+(?:cread[oa]|fundad[oa]|lanxad[oa]|descubiert[oa])\b", re.I), "origen_en", "historia"),
    (re.compile(r"(?:los\s+)?(?P<subj>[\wáéíóúñ]{4,30})s?\s+(?:son|existen)\s+(?:varios|diversos|múltiples)?[^.;]*?(?:tipos|clases|variantes)\s+de\b", re.I), "tiene_tipos", "tipo"),
]

_ASPECT_CUES = [
    ("tipo", re.compile(r"\btipos?\b|\bclases\b|\bvariantes\b|\bclasificaci", re.I)),
    ("uso", re.compile(r"\bse utiliza|\bse usa|\bsirve para|\busos\b|\baplicaciones", re.I)),
    ("mecanismo", re.compile(r"\bfunciona|\bproceso\b|\bmediante\b|\bconsiste en|\bmétodo\b", re.I)),
    ("historia", re.compile(r"\bhistoria\b|\bfundad|\bcread[oa]\b|\borgen\b|\baño\b|\b1\d{3}\b|\b20\d{2}\b|\b\d{4}\s*a\.?\s*C\b", re.I)),
    ("definicion", re.compile(r" es un | es una | es el | es la | es todo | significa", re.I)),
]


def _normalize_concept(text: str) -> str:
    from arca.retrieval import strip_accents, tokenize

    tokens = tokenize(text)
    if not tokens:
        return ""
    return " ".join(tokens[:4]).strip()


def classify_aspect(sentence: str) -> str:
    for aspect, pattern in _ASPECT_CUES:
        if pattern.search(sentence):
            return aspect
    return "dato"


def _hv_bytes(vector: np.ndarray) -> bytes:
    return np.packbits(vector).tobytes()


class EvidenceGraph:
    def __init__(self, store: MemoryStore, max_triples: int = 500_000) -> None:
        self.store = store
        self.max_triples = max(1000, max_triples)
        store.ensure_graph_tables()

    def concept_id(self, name: str) -> int | None:
        normalized = _normalize_concept(name)
        if not normalized:
            return None
        with self.store.connect() as db:
            row = db.execute("SELECT id FROM concepts WHERE name=?", (normalized,)).fetchone()
            if row:
                return int(row["id"])
            hv = _hv_bytes(hdc.encode(normalized))
            cursor = db.execute("INSERT INTO concepts(name,hv) VALUES(?,?) ON CONFLICT(name) DO NOTHING", (normalized, hv))
            if cursor.lastrowid:
                return int(cursor.lastrowid)
            row = db.execute("SELECT id FROM concepts WHERE name=?", (normalized,)).fetchone()
            return int(row["id"]) if row else None

    def ingest_document(self, document: dict[str, Any]) -> int:
        """Mine one fetched document into triples + passages."""
        content = str(document.get("content") or "")
        url = str(document.get("url") or "")
        title_concept = self.concept_id(str(document.get("title") or ""))
        from arca.retrieval import split_sentences

        added = 0
        for sentence in split_sentences(content):
            aspect = classify_aspect(sentence)
            subject_id, predicate, object_text = None, None, ""
            for pattern, pred, pred_aspect in _PATTERNS:
                match = pattern.search(sentence)
                if not match:
                    continue
                groups = match.groupdict()
                subj_text = groups.get("subj")
                resolved = self.concept_id(subj_text) if subj_text else None
                if resolved is None and title_concept is not None:
                    resolved, object_text = title_concept, sentence[:180]
                else:
                    object_text = (groups.get("obj") or "")[:160]
                subject_id, predicate, aspect = resolved, pred, pred_aspect
                break
            if subject_id is None:
                subject_id = title_concept
                predicate = "menciona"
                object_text = sentence[:120]
            if subject_id is None:
                continue
            added += self.store.add_triple(subject_id, predicate, object_text, sentence, aspect, url)
        return added

    def backfill(self, limit: int = 2000) -> dict[str, int]:
        """Bulk-mine already-cached documents (disk does the learning)."""
        with self.store.connect() as db:
            rows = [dict(row) for row in db.execute(
                "SELECT title,url,content FROM documents ORDER BY id DESC LIMIT ?", (limit,))]
        mined = 0
        for row in rows:
            mined += self.ingest_document(row)
        return {"documents": len(rows), "triples_added": mined}

    def passages_for(self, subject: str, aspects: list[str], exclude_aspects: list[str] | None = None, limit: int = 12) -> list[dict[str, Any]]:
        if not aspects:
            return []
        subject_ids = self._subject_ids(subject)
        if not subject_ids:
            return []
        placeholders = ",".join("?" for _ in aspects)
        aspect_clause = f"aspect IN ({placeholders})"
        excluded = exclude_aspects or []
        semicolon = ""
        if excluded:
            excl_ph = ",".join("?" for _ in excluded)
            aspect_clause += f" AND aspect NOT IN ({excl_ph})"
        id_ph = ",".join("?" for _ in subject_ids)
        with self.store.connect() as db:
            rows = [dict(row) for row in db.execute(
                f"SELECT t.passage,t.aspect,t.object_text,t.source_url,c.name AS subject "
                f"FROM triples t JOIN concepts c ON c.id=t.subject_id "
                f"WHERE t.subject_id IN ({id_ph}) AND {aspect_clause} ORDER BY t.id DESC LIMIT ?",
                [*subject_ids, *aspects, *excluded, limit * 4])]
        seen: set[str] = set()
        unique = []
        for row in rows:
            key = row["passage"][:60].casefold()
            if key in seen:
                continue
            seen.add(key)
            unique.append(row)
        return unique[:limit]

    def _subject_ids(self, subject: str) -> list[int]:
        """Resolve a topic to concept ids. Compound concepts sharing the same
        leading token qualify ONLY if semantically related to the base concept
        (HDC similarity), so 'barco pasajero' (a ship type) is included while
        'barco valdeorra' (a municipality) is not."""
        normalized = _normalize_concept(subject)
        base = normalized.split()[0] if normalized else ""
        base_hv: bytes | None = None
        exact: int | None = None
        with self.store.connect() as db:
            row = db.execute("SELECT id, hv FROM concepts WHERE name=?", (base,)).fetchone()
            if row:
                exact, base_hv = int(row["id"]), row["hv"]
            rows: list[tuple[int, bytes]] = [r for r in db.execute(
                "SELECT id, hv FROM concepts WHERE name LIKE ?", (f"{base} %",))]
        if exact is not None and base_hv is not None:
            base_bits = np.unpackbits(np.frombuffer(base_hv, dtype=np.uint8))
            selected = [exact]
            for cid, hv_bytes in rows:
                if cid == exact:
                    continue
                cand = np.unpackbits(np.frombuffer(hv_bytes, dtype=np.uint8))
                agree = float(np.count_nonzero(base_bits == cand) / hdc.D)
                if agree >= hdc.RELATED:
                    selected.append(cid)
            return selected
        if exact is not None:
            return [exact]
        return [cid for cid, _ in rows] if rows else []

    def prune_if_needed(self) -> int:
        with self.store.connect() as db:
            count = int(db.execute("SELECT COUNT(*) FROM triples").fetchone()[0])
            if count <= self.max_triples:
                return 0
            db.execute(
                "DELETE FROM triples WHERE id IN (SELECT id FROM triples ORDER BY id ASC LIMIT ?)",
                (count - self.max_triples,))
            return count - self.max_triples
