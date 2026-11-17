from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_TOKEN_SPLIT = re.compile(r"[^\wÁÉÍÓÚÑáéíóúñ]+", re.UNICODE)
_STOPWORDS = frozenset("""
que qué como cómo quien quién cuando dónde cuál cual para por con sin sobre entre desde hasta
los las del sus esta este esto estos estas ese esa eso aquel aquella son ser es fue muy mas más
todo toda todos todas pero porque aunque si no ni ya hay ha han haber fue the and for with from
that this what who how why where which you your can will not are was were has have its into
""".split())

_JUNK = re.compile(r"(jump to content|main menu|move to sidebar|toggle .{0,20}contents|log in|create account|edit edit source|personal tools|privacy policy|donate|contribute help|random article|print/export|wikitext|upload file)", re.I)
_NOISE = re.compile(
    r"(\bdice:\s|\bresponder\b|\bcomenta\b|ir al (contenido|episodio)|\bescuchar\b|"
    r"\b\d{1,2}:\d{2}\s*(am|pm|hs)\b|\bsuscr[ií]bet\b|\bcookie[s]?\b|"
    r"derechos de autor.*privacidad|displaystyle|\{\\\\|editar datos en wikidata|"
    r"\d\.\d+(\.\d+)?\s+[A-ZÁÉÍÓÚÑ]|"
    r"licencia creative commons|pol[íi]tica de privacidad|t[eé]rminos de uso|"
    r"esta p[áa]gina se edit[oó]|disponible bajo la licencia|pueden aplicarse cl[aá]usulas|"
    r"c[oó]mo citar|enlaces externos|alguna pregunta|chatear|wikimedia foundation|"
    r"acerca de wikipedia|avance de responsabilidad|contactar con wikipedia|\bv[íi]nculo\b.*semi[oó]tico|"
    r"control de autoridades|proyectos wikimedia|identificadores|\bGND\b|\bLCCN\b|\bBNE\b|\bQ\d{6,}\b|"
    r"multimedia:\s|datos:\s+Q\d+)", 
    re.I,
)


@dataclass(slots=True)
class Sentence:
    text: str
    score: float
    title: str
    url: str


def strip_accents(text: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFD", text) if unicodedata.category(char) != "Mn")


def _stem(token: str) -> str:
    """Crude Spanish plural folding so 'barcos' matches query 'barco'."""
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    return [_stem(token) for token in (_TOKEN_SPLIT.split(text.casefold())) if len(_stem(token)) > 2 and token not in _STOPWORDS]


def _split_long(chunk: str, limit: int = 550) -> list[str]:
    """Word-boundary wrap for oversized single sentences (encyclopedia leads),
    padding a final period so downstream filters keep them."""
    if len(chunk) <= limit:
        return [chunk]
    pieces: list[str] = []
    buffer = ""
    for word in chunk.split(" "):
        buffer = f"{buffer} {word}".strip()
        if len(buffer) >= limit:
            pieces.append(buffer)
            buffer = ""
    if buffer.strip():
        pieces.append(buffer.strip())
    normalized = []
    for piece in pieces:
        piece = piece.strip()
        if len(piece) >= 40:
            normalized.append(piece if piece[-1] in ".!?…;" else f"{piece}.")
    return normalized


def split_sentences(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    raw_parts: list[str] = []
    for part in _SENTENCE_SPLIT.split(cleaned):
        part = part.strip()
        if not part:
            continue
        if len(part) <= 600:
            raw_parts.append(part)
        else:
            raw_parts.extend(_split_long(part))
    sentences = []
    for part in raw_parts:
        if not (40 <= len(part) <= 700):
            continue
        if not re.search(r"[.!?…:]$", part):
            continue
            continue
        words = part.split()
        if len(words) < 6:
            continue
        if _JUNK.search(part) or _NOISE.search(part):
            continue
        sentences.append(part)
    return sentences


_DEFINITION_CUES = (" es un ", " es una ", " es el ", " es la ", " es todo ", " es toda ", " significa", " se utiliza", " se usa", " permite", " consiste", " sirve para", " funciona", " son ")


def score_sentence(query_tokens: list[str], sentence: str) -> float:
    if not query_tokens:
        return 0.0
    tokens = set(tokenize(sentence))
    normalized_tokens = {strip_accents(token) for token in tokens}
    if not tokens:
        return 0.0
    # Distinct concept matching: repeated mentions of the SAME query token
    # ('Barcos ... Barco ...' inside a footballer bio) must not inflate
    # coverage beyond a sentence that defines the concept once.
    unique_query = set(query_tokens)
    matched_tokens = {raw for raw in unique_query if raw in tokens or strip_accents(raw) in normalized_tokens}
    coverage = len(matched_tokens) / len(unique_query)
    density = len(matched_tokens) / max(len(tokens), 1) * 4.0
    score = coverage * 0.8 + min(density, 1.0) * 0.2
    lowered = sentence.casefold()
    if lowered.rstrip().endswith("?"):
        score *= 0.35
    if _META_OPENERS.match(lowered):
        score *= 0.2
    if any(cue in lowered for cue in _DEFINITION_CUES):
        score *= 1.35
    return min(score, 1.5)


_DEFINITION_CUES = (" es un ", " es una ", " es el ", " es la ", " significa", " se utiliza", " se usa", " permite", " consiste", " sirve para", " funciona", " son ")
_META_OPENERS = re.compile(r"^(lea|lee|ver también|mira|introduction to|related|artículo|siguiente|anterior)\b", re.I)

def concept_tokens(query: str) -> list[str]:
    """Distinctive tokens of a query: the two longest substantive words when
    available ('programación orientada a objetos', 'tipos de barcos'),
    otherwise just the longest one."""
    tokens = sorted({token for token in tokenize(query)}, key=len, reverse=True)
    return tokens[:2] if len(tokens) >= 2 else tokens[:1]


def rank_evidence(query: str, documents: list[dict[str, Any]], limit: int = 8) -> list[Sentence]:
    query_tokens = [strip_accents(token) for token in tokenize(query)]
    ranked: list[Sentence] = []
    for doc_index, document in enumerate(documents):
        content = str(document.get("content") or document.get("snippet") or "")
        title = str(document.get("title", ""))
        url = str(document.get("url", ""))
        rank_bonus = 1.0 + max(0, 2 - doc_index) * 0.15
        doc_sentences = split_sentences(content)
        total = max(len(doc_sentences), 1)
        for position, sentence in enumerate(doc_sentences):
            score = score_sentence(query_tokens, sentence)
            if score <= 0:
                continue
            lead_bonus = 1.0 + max(0.0, 1.0 - position / total) * 0.35
            ranked.append(Sentence(sentence, score * lead_bonus * rank_bonus, title, url))
    ranked.sort(key=lambda item: item.score, reverse=True)
    selected: list[Sentence] = []
    fingerprints: set[str] = set()
    for candidate in ranked:
        fingerprint = strip_accents(candidate.text)[:60].casefold()
        if any(fingerprint[:40] == seen[:40] or SequenceMatcher(None, fingerprint, seen).ratio() > 0.75 for seen in fingerprints):
            continue
        fingerprints.add(fingerprint)
        selected.append(candidate)
        if len(selected) >= limit:
            break
    return selected


def _fuzzy_contains(haystack: str, needle: str, threshold: float = 0.84) -> bool:
    """Accent-insensitive containment with typo tolerance via sequence ratio."""
    normalized_haystack = " " + strip_accents(haystack).casefold() + " "
    normalized_needle = strip_accents(needle).casefold()
    if normalized_needle in normalized_haystack:
        return True
    tokens = set(_TOKEN_SPLIT.split(normalized_haystack))
    return any(SequenceMatcher(None, token, normalized_needle).ratio() >= threshold for token in tokens)


def compose_prose(query: str, documents: list[dict[str, Any]], max_chars: int = 1200, min_score: float = 0.25) -> tuple[str, list[str]] | None:
    """Conversational paragraph built from real evidence: definition first,
    supporting sentences after, joined as flowing prose instead of bullets."""
    best = rank_evidence(query, documents, limit=10)
    strong = [item for item in best if item.score >= min_score]
    if not strong:
        return None
    definitional = bool(re.match(r"^(qué es|que es|qué son|what is|what are|define)", strip_accents(query.strip().lstrip("¿¡ \t")), re.I))
    lowered_query = strip_accents(query).casefold()
    wants_how = "como funciona" in lowered_query or "por que" in lowered_query

    def is_lead(item: Sentence) -> bool:
        lowered = item.text.casefold()
        definitional_cues = (
            " es un ", " es una ", " es el ", " es la ", " es todo ", " es toda ",
            " significa", " consiste", " se define", " se denomina", " fue un ", " fue una ",
        )
        if definitional and any(cue in lowered for cue in definitional_cues):
            return True
        if wants_how and any(cue in lowered for cue in ("funciona", "proceso", "mediante", "permite", "se basa")):
            return True
        return False

    leads = [item for item in strong if is_lead(item)]
    ordered = (leads + [item for item in strong if item not in leads]) if definitional or wants_how else strong
    concepts = concept_tokens(query)

    def _common_noun_use(text: str, concept: str) -> bool:
        """The concept must appear as a common noun (lowercase, or starting the
        sentence). Mid-sentence capitalized hits are proper nouns ('Hernán
        Barcos'), not the concept the user asked about."""
        pattern = re.compile(rf"(?<!\w){re.escape(concept)}(?:s|es)?(?!\w)", re.I)
        for match in pattern.finditer(text):
            word = match.group(0)
            boundary_before = text[:match.start()].rstrip()
            at_sentence_start = match.start() == 0 or boundary_before.endswith((".", "!", "?", "¿", "¡", ":", ";"))
            if word == word.lower() or at_sentence_start:
                return True
        return False

    leads = [item for item in strong if is_lead(item)]
    ordered = (leads + [item for item in strong if item not in leads]) if definitional or wants_how else strong
    parts: list[Sentence] = []
    length = 0
    for item in ordered:
        if concepts and len(parts) >= 1:
            on_concept = all(_fuzzy_contains(item.text, token) for token in concepts)
            natural_use = all(_common_noun_use(item.text, token) for token in concepts)
            if not (on_concept and natural_use):
                # Supporting sentences must stay on-concept: a perfect definition
                # followed by namesakes ('Valentín Barco') reads like garbage.
                continue
        piece = item.text.strip()
        if length + len(piece) + 1 > max_chars:
            break
        if parts and SequenceMatcher(None, strip_accents(piece)[:80].casefold(), strip_accents(parts[-1].text)[:80].casefold()).ratio() > 0.6:
            continue
        parts.append(Sentence(piece, item.score, item.title, item.url))
        length += len(piece) + 1
        if len(parts) >= 4:
            break
    if not parts:
        return None
    prose = " ".join(item.text for item in parts)
    used_urls: list[str] = []
    for item in parts:
        if item.url and item.url not in used_urls:
            used_urls.append(item.url)
    sources = "\n\nFuentes:\n" + "\n".join(f"- {url}" for url in used_urls[:3]) if used_urls else ""
    return prose + sources, used_urls


def compose_answer(query: str, documents: list[dict[str, Any]], max_chars: int = 1200, min_score: float = 0.25) -> tuple[str, list[str]] | None:
    """Backwards-compatible alias now returning conversational prose."""
    return compose_prose(query, documents, max_chars=max_chars, min_score=min_score)
