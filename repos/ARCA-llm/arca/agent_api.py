from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Protocol

from arca.assistant import CognitiveAssistant
from arca.conversation import ConversationIntelligence, ConversationMemory, ConversationState, ResponseQuality
from arca.graph import EvidenceGraph
from arca.model import Expediente, TraceStep
from arca.retrieval import _fuzzy_contains, compose_answer, concept_tokens, strip_accents, tokenize
from arca.web import WebEvidenceClient


@dataclass(frozen=True, slots=True)
class AgentResponse:
    text: str
    success: bool
    trace: tuple[dict[str, Any], ...]
    telemetry: dict[str, Any]


class AgentBackend(Protocol):
    def respond(self, message: str, session_id: str = "default") -> AgentResponse: ...


_META_SECTION = re.compile(r"(?im)^\s*(objective|important details|work state|next move|relevant files|blocked|active)\s*$")
_STATE_TEMPLATE_MARKERS = ("objective", "important details", "work state", "next move", "relevant files")
_TOPIC_HINTS = re.compile(r"(el usuario está preguntando[^\n.]*|el usuario está buscando[^\n.]*|user is asking about[^\n.]*|asking about[^\n.]*)", re.I)
_TITLE_PROMPT = re.compile(r"\b(generate a (short )?title|title for (this |the )?(conversation|session|chat)|sugiere un t[ií]tulo)\b", re.I)

_DEFINITION_QUERY = re.compile(r"^(qué es|que es|qué son|what is|what are|quiénes son|define|cómo funciona|como funciona|cómo se usa|como se usa)\b", re.I)
_TIME_QUERY = re.compile(r"^[\s¿¡]*(?:qué|que)\s+hora\b|^[\s¿¡]*hora\s*[?.!]*$|me (?:dicen?|pasás?) la hora|^[\s¿¡]*(?:qué|que) día\b|^[\s¿¡]*(?:qué|que) fecha\b|fecha de hoy", re.I)
_CONTINUATION_QUERY = re.compile(r"^(?:contame|dime|decime)\s+más\b|^más\s*[.!]?$\b|^¿?y?\s*(?:por qué|cuándo|cómo|donde|quién)\b|^expand[ií]\b|^detallam[eé]\b|^segu[ií]\b|^sigue\b|^¿\s*y\s+cuándo\b", re.I)
_SOCIAL: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("greeting", ("hola", "buenas", "buenos días", "buenos dias", "buenas tardes", "buenas noches", "hey", "hello", "hi", "qué tal", "que tal", "cómo andás", "comoandas")),
    ("thanks", ("gracias", "muchas gracias", "thank you", "thanks", "genial gracias")),
    ("bye", ("adiós", "adios", "chau", "hasta luego", "nos vimos", "hasta mañana", "bye")),
    ("howareyou", ("cómo estás", "como estas", "cómo te va", "todo bien")),
    ("identity", ("quién eres", "quién sos", "qué eres", "qué podés hacer", "qué puedes hacer", "ayuda", "help", "capacidades")),
)

_SOCIAL_REPLIES: dict[str, list[str]] = {
    "greeting": ["Hola. ¿En qué puedo ayudarte? Preguntame algo y busco evidencia real para responderte.", "¡Hola! Estoy listo. ¿Qué necesitás saber?"],
    "thanks": ["De nada. Estoy cuando me necesites.", "Un placer. ¿Algo más en lo que pueda ayudarte?"],
    "bye": ["Hasta luego. Tu contexto y memoria quedan guardados.", "Nos vemos. Todo tu conocimiento acumulado sigue acá."],
    "howareyou": ["Funcionando correctamente, con memoria intacta. ¿En qué te ayudo?"],
    "identity": ["Soy ARCA: arquitectura cognitiva local de recursos mínimos. No genero texto inventado: recupero evidencia de la web y de mi memoria persistente (hechos, documentos, grafo y procedimientos), y respondo citando fuentes. Puedo recordar hechos ('recuerda que...'), aprender procedimientos ('recuerda el procedimiento X: 1) ...'), decirte la hora local, y responder preguntas buscando en internet."],
}

_PROCEDURE_TEACH = re.compile(r"(?:recuerda|guarda|aprende)\s+(?:el\s+|la\s+)?procedimiento\s+(.+?)\s*[:：]\s*(.+)", re.I | re.S)
_PROCEDURE_SPLIT = re.compile(r"\s*(?:\d+\s*[\.\)\:]|-|;|\n)\s*")
_PURE_SOCIAL = re.compile(r"^[¿¡\s]*(%s)[\s!.?…]*$" % "|".join(re.escape(phrase) for _, phrases in _SOCIAL for phrase in phrases), re.I)

_WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MONTHS = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def _extract_topic(text: str) -> str:
    match = _TOPIC_HINTS.search(text)
    if match:
        return match.group(1).strip()
    sections = _META_SECTION.split(text)
    for index in range(1, len(sections) - 1, 2):
        label = sections[index].strip().casefold()
        value = sections[index + 1].strip()
        if label == "objective" and value and not value.startswith("("):
            return value.splitlines()[0].strip()
    return ""


def _meta_reply(query: str) -> tuple[str, tuple[dict[str, Any], ...], dict[str, Any]] | None:
    lowered = query.casefold()
    marker_hits = sum(1 for marker in _STATE_TEMPLATE_MARKERS if marker in lowered)
    is_state_template = marker_hits >= 3 or bool(_STATE_TEMPLATE_MARKERS and marker_hits >= 2 and len(query) > 300)
    is_title_prompt = bool(_TITLE_PROMPT.search(lowered)) and len(query) > 120
    if not is_state_template and not is_title_prompt:
        return None
    topic = _extract_topic(query)
    if is_title_prompt:
        title = " ".join(topic.split()[:8]) if topic else "Conversación con ARCA"
        return title, (asdict(TraceStep("meta.title", "deterministic internal template reply")),), {"success": True, "internal": "title"}
    objective = topic or "(none)"
    text = (
        f"Objective\n{objective}\n"
        f"Important Details\nEl usuario interactúa con ARCA; las respuestas se construyen con evidencia local y web citando fuentes.\n"
        f"Work State\nActive\n"
        f"Active Tasks\n(none)\n"
        f"Blocked\n(none)\n"
        f"Next Move\n(none)\n"
        f"Relevant Files\n(none)"
    )
    return text, (asdict(TraceStep("meta.state", "deterministic internal template reply")),), {"success": True, "internal": "state"}


def _social_reply(text: str) -> str | None:
    stripped = text.strip().strip("¿¡").strip()
    if len(stripped) > 48:
        return None
    match = _PURE_SOCIAL.match(stripped)
    if not match:
        return None
    lowered = stripped.casefold()
    for kind, phrases in _SOCIAL:
        if any(lowered.startswith(phrase) or phrase in lowered for phrase in phrases):
            replies = _SOCIAL_REPLIES[kind]
            return replies[abs(hash(lowered)) % len(replies)]
    return None


def _time_reply(text: str) -> str | None:
    stripped = text.strip().strip("¿¡").casefold()
    if len(stripped) > 40 or not _TIME_QUERY.match(text.strip()):
        return None
    now = time.localtime()
    if "día" in stripped or "dia" in stripped or "fecha" in stripped:
        return f"Hoy es {_WEEKDAYS[now.tm_wday]} {now.tm_mday} de {_MONTHS[now.tm_mon - 1]} de {now.tm_year}."
    return f"Son las {now.tm_hour:02d}:{now.tm_min:02d} de tu zona horaria local."


def _parse_procedure_teaching(text: str) -> tuple[str, list[str], list[str]] | None:
    match = _PROCEDURE_TEACH.search(text)
    if not match:
        return None
    name = match.group(1).strip().strip('"')
    body = match.group(2)
    steps = [step.strip(" .") for step in _PROCEDURE_SPLIT.split(body) if step.strip(" .")]
    if len(steps) == 1 and "," in steps[0] and len(steps[0]) > 120:
        steps = [part.strip() for part in steps[0].split(",") if part.strip()]
    triggers = [token.casefold() for token in re.findall(r"[\wÁÉÍÓÚÑáéíóúñ]{3,}", name)]
    return name, steps[:12], triggers


_FOLLOWUP_WORDS = frozenset("""
cómo como por porque cuándo cuando más mas qué que se es y a del la el los las un unos otra mucho
detallame seguime expandime contame dime decime créo creó inventó inventaron inventado inventada
nació nacio nacido origen historia actualidad actualmente moderno antiguo antes ahora hoy
funciona funcionan funcionamiento tipos tipo proceso mecanismo usa utiliza creado creada fundado
quien quién cual cuales eran fue seria será puede tiene sobre eso esa ese otraver más aún ya
""".split())


def _is_followup_word(token: str) -> bool:
    return token in _FOLLOWUP_WORDS or not token.isalpha()


class ARCAAgentBackend:
    """Evidence-first backend: answers are composed from retrieved sources, never invented."""

    def __init__(
        self,
        model_path: str | Path,
        db_path: str | Path = "arca.db",
        max_turns: int = 12,
        fetch_bytes: int = 500_000,
        answer_chars: int = 1200,
        max_web_docs: int = 3,
        search_limit: int = 5,
        max_docs: int = 500,
        max_triples: int = 500_000,
    ) -> None:
        self.model_path = Path(model_path)
        self.memory_path = self.model_path.with_suffix(".sessions.json")
        self.sessions = ConversationMemory(self.memory_path, max_turns=max_turns)
        self.assistant = CognitiveAssistant(db_path, web=WebEvidenceClient(max_bytes=fetch_bytes), model=None)
        self.assistant.memory.max_docs = max(1, int(max_docs))
        self.answer_chars = answer_chars
        self.max_web_docs = max_web_docs
        self.search_limit = search_limit
        self.graph = EvidenceGraph(self.assistant.memory, max_triples=max_triples)

    def respond(self, message: str, session_id: str = "default") -> AgentResponse:
        normalized = message.strip()
        meta = _meta_reply(normalized)
        if meta is not None:
            text, trace, telemetry = meta
            telemetry.update({"session_id": session_id, "intent": "internal_meta", "context_turns": 0, "salient_facts": 0, "model": "ARCA-evidence", "external_weights": False})
            return AgentResponse(text, True, trace, telemetry)

        state: ConversationState = self.sessions.load(session_id)

        clock = _time_reply(normalized)
        if clock is not None:
            step = TraceStep("context.clock", "local system time, no network needed")
            self._record_turn(state, session_id, normalized, clock)
            return AgentResponse(clock, True, (asdict(step),), self._base_telemetry(session_id, "context_time"))

        if state.pending_senses:
            chosen = self._resolve_pending_sense(normalized, state.pending_senses)
            if chosen is not None:
                state.pending_senses = []
                self.sessions.save(state)
                return self._answer_flow(chosen, "memory_read", state, session_id)
            # user moved on to something else entirely: drop stale senses
            if len(normalized) > 30 or "?" in normalized:
                state.pending_senses = []
                self.sessions.save(state)

        social = _social_reply(normalized)
        if social is not None:
            text, trace, telemetry = social, (asdict(TraceStep("social.reply", "deterministic localized template")),), {"success": True}
            self._record_turn(state, session_id, normalized, text)
            telemetry.update({"session_id": session_id, "intent": "social"})
            return AgentResponse(text, True, trace, self._finalize(telemetry, state))

        resolved = ConversationIntelligence.resolve_references(normalized, state)
        intent = ConversationIntelligence.classify(resolved)
        self.sessions.add(state, "user", resolved)

        is_continuation = bool(_CONTINUATION_QUERY.match(resolved.strip()))
        prev_topic = state.last_topic
        # A follow-up must not introduce a brand-new substantive subject (e.g.
        # "¿cómo funciona YouTube?" after talking about barco is a fresh query).
        if is_continuation and prev_topic:
            intro_tokens = {token.casefold() for token in tokenize(resolved) if not _is_followup_word(token)}
            if intro_tokens and not (intro_tokens <= {prev_topic.casefold()}):
                is_continuation = False
        if is_continuation and prev_topic:
            text, trace, telemetry = self._continuation_answer(resolved, state)
            self.sessions.add(state, "assistant", text)
            self.sessions.compress(state)
            telemetry.update({"session_id": session_id, "intent": "continuation", **self._core(state)})
            return AgentResponse(text, bool(telemetry.get("success")), trace, self._finalize(telemetry, state))

        if intent == "memory_write":
            procedure = self._procedure_teach(resolved)
            if procedure is not None:
                text, trace, telemetry = procedure
                self.sessions.add(state, "assistant", text)
                telemetry.update({"session_id": session_id, "intent": "procedure_write", **self._core(state)})
                return AgentResponse(text, bool(telemetry.get("success")), trace, self._finalize(telemetry, state))
            text, trace, telemetry = self._via_assistant(resolved)
            self.sessions.add(state, "assistant", text)
            telemetry.update({"session_id": session_id, "intent": intent})
            telemetry.update(ResponseQuality.telemetry(text, ""))
            return AgentResponse(text, bool(telemetry.get("success")), trace, self._finalize({**telemetry, "_text": text}, state))

        if intent in {"planning", "memory_read"}:
            recalled = self._procedure_recall(resolved, intent)
            if recalled is not None:
                text, trace, telemetry = recalled
                self.sessions.add(state, "assistant", text)
                telemetry.update({"session_id": session_id, "intent": "procedure_recall", **self._core(state)})
                return AgentResponse(text, True, trace, self._finalize(telemetry, state))

        response = self._answer_flow(resolved, intent, state, session_id)
        return response

    def _record_turn(self, state: ConversationState, session_id: str, user_text: str, assistant_text: str) -> None:
        self.sessions.add(state, "user", user_text)
        self.sessions.add(state, "assistant", assistant_text)

    def _core(self, state: ConversationState) -> dict[str, Any]:
        return {"context_turns": len(state.turns), "salient_facts": len(state.salient_facts), "model": "ARCA-evidence", "external_weights": False}

    def _base_telemetry(self, session_id: str, intent: str) -> dict[str, Any]:
        return {"session_id": session_id, "intent": intent, "model": "ARCA-evidence", "external_weights": False}

    def _finalize(self, telemetry: dict[str, Any], state: ConversationState) -> dict[str, Any]:
        telemetry.update(self._core(state))
        telemetry.update(ResponseQuality.telemetry(str(telemetry.get("_text", "")), ""))
        return {k: v for k, v in telemetry.items() if not k.startswith("_")}

    def _answer_flow(self, query: str, intent: str, state: ConversationState, session_id: str) -> AgentResponse:
        text, trace, telemetry = self._answer(query, intent, state)
        self.sessions.add(state, "assistant", text)
        self.sessions.compress(state)
        telemetry.update({"session_id": session_id, "intent": intent})
        telemetry.update(ResponseQuality.telemetry(text, ""))
        success = bool(telemetry.get("success", True)) and not bool(telemetry.get("quality_warning", False))
        return AgentResponse(text, success, trace, self._finalize({**telemetry, "_text": text}, state))

    def _answer(self, query: str, intent: str, state: ConversationState) -> tuple[str, tuple[dict[str, Any], ...], dict[str, Any]]:
        if intent == "calculation":
            return self._via_assistant(query)

        memory = self.assistant.memory
        trace_steps: list[TraceStep] = []
        concepts = self._concept_tokens(query)

        assertions = memory.recall(query)
        if assertions:
            lines = [f"- {row['subject']} {row['predicate']} {row['object']}" for row in assertions[:6]]
            text = "Según mi memoria persistente:\n" + "\n".join(lines)
            trace_steps.append(TraceStep("memory.assertions", f"recalled {len(assertions)} stored assertion(s)"))
            record = Expediente(query, "memory_recall", result=assertions, trace=trace_steps, telemetry={"success": True})
            memory.save_episode(record)
            self._track_topic(state, concepts, ["definicion"])
            return text, tuple(asdict(step) for step in trace_steps), {"success": True, "sources": len(assertions), "evidence_origin": "memory"}

        documents = memory.search_documents(query, limit=self.search_limit)
        if documents:
            trace_steps.append(TraceStep("memory.cache", f"retrieved {len(documents)} local document(s)"))

        definitional = bool(_DEFINITION_QUERY.match(query.strip().lstrip("¿¡ \t")))
        composed = None if definitional else compose_answer(query, documents, max_chars=self.answer_chars)
        source = "memory"
        if composed is not None:
            ok, reason = self._accept(query, composed[0], documents)
            if not ok:
                trace_steps.append(TraceStep("memory.offtopic", "cached evidence does not address the query subject"))
                composed = None

        if composed is None:
            fetched_urls, fetched_docs, alt_senses, has_dominant = self._fetch_evidence(query, trace_steps)
            if not has_dominant and len(alt_senses) >= 2:
                clarify = self._ask_which_sense(query, alt_senses, state, trace_steps)
                return clarify
            recent = fetched_docs if fetched_docs else documents
            if recent:
                composed = compose_answer(query, recent, max_chars=self.answer_chars)
                if composed is not None:
                    ok, reason = self._accept(query, composed[0], recent)
                    if not ok:
                        trace_steps.append(TraceStep("web.offtopic", "fetched evidence does not address the query subject"))
                        composed = None
                    else:
                        source = "web" if fetched_docs else "memory"
                        if reason == "relaxed_by_title":
                            trace_steps.append(TraceStep("gate.relaxed", "exact-title document vouches for the evidence"))
            if composed is not None and fetched_docs:
                mined = sum(self.graph.ingest_document(doc) for doc in fetched_docs)
                if mined:
                    trace_steps.append(TraceStep("graph.mine", f"mined {mined} triple(s) into evidence graph"))
                planned = self._try_planner(query, definitional, fetched_docs, state)
                if planned is not None:
                    note = ""
                    if has_dominant and alt_senses:
                        note = f" (Si preguntabas por {alt_senses[0][0]}, avisame.)"
                    record = Expediente(query, f"{source}_planned", result=planned[0], trace=trace_steps, telemetry={"success": True, "sources": len(planned[1])})
                    memory.save_episode(record)
                    self._track_topic(state, concepts, planned[2])
                    return planned[0] + note, tuple(asdict(step) for step in trace_steps), {"success": True, "sources": len(planned[1]), "evidence_origin": source, "planner": True}

        if composed is None:
            hint = "No encontré evidencia suficiente para responder con fuentes confiables."
            hint += " Probá reformular la pregunta, agregar más contexto o indicar el tema exacto que buscás."
            trace_steps.append(TraceStep("no.evidence", "insufficient evidence after local memory and web lookup"))
            record = Expediente(query, "clarify", result=hint, trace=trace_steps, telemetry={"success": False})
            memory.save_episode(record)
            return hint, tuple(asdict(step) for step in trace_steps), {"success": False, "sources": 0}

        text, used_urls = composed
        trace_steps.append(TraceStep("compose.extractive", f"answer built from {source} evidence", evidence=tuple(used_urls)))
        record = Expediente(query, f"{source}_evidence", result=text, trace=trace_steps, telemetry={"success": True, "sources": len(used_urls)})
        memory.save_episode(record)
        self._track_topic(state, concepts, [])
        return text, tuple(asdict(step) for step in trace_steps), {"success": True, "sources": len(used_urls), "evidence_origin": source}

    def _try_planner(self, query: str, definitional: bool, fetched_docs: list[dict[str, Any]], state: ConversationState) -> tuple[str, list[str], list[str]] | None:
        from arca.planner import plan_answer

        concepts = self._concept_tokens(query)
        subject = concepts[0] if concepts else ""
        if not subject:
            return None
        aspects_needed = ["mecanismo", "uso", "dato"] if re.match(r"c[oó]mo funciona", query.strip().lstrip("¿¡ \t"), re.I) else ["definicion", "tipo", "uso"]
        passages = self.graph.passages_for(subject, aspects_needed, exclude_aspects=[], limit=10)
        if len(passages) < 2:
            return None
        candidates = [{"passage": passage["passage"], "aspect": passage["aspect"], "source_url": passage["source_url"]} for passage in passages]
        intent_key = "como_funciona" if aspects_needed[0] == "mecanismo" else "que_es"
        prose, urls, filled = plan_answer(intent_key, subject, candidates, covered_aspects=list(state.covered_aspects or []))
        if not prose or not filled:
            return None
        return prose, urls, filled

    def _track_topic(self, state: ConversationState, concepts: list[str], aspects: list[str]) -> None:
        if not concepts:
            return
        state.last_topic = concepts[-1] if len(concepts) > 1 else concepts[0]
        for aspect in aspects:
            if aspect not in state.covered_aspects:
                state.covered_aspects.append(aspect)
        del state.covered_aspects[:-12]
        self.sessions.save(state)

    def _continuation_answer(self, message: str, state: ConversationState) -> tuple[str, tuple[dict[str, Any], ...], dict[str, Any]]:
        topic = state.last_topic
        wants_why = bool(re.search(r"por qué|porque|cuándo|cuando|origen|historia|inventó|invento|creó|creo|nació|nacio", message, re.I))
        wants_how = bool(re.search(r"cómo|como\s+funciona|mecanismo|proceso", message, re.I))
        if wants_why:
            wanted = ["historia", "dato"]
        elif wants_how:
            wanted = ["mecanismo", "uso"]
        else:
            wanted = ["tipo", "uso", "mecanismo", "historia"]
        excluded = list(state.covered_aspects)
        passages = self.graph.passages_for(topic, wanted, exclude_aspects=excluded, limit=8)
        if passages and len(passages) < 1:
            passages = []
        if not passages:
            # Local graph is too sparse: enrich it live by re-fetching the topic
            # under the requested aspect, keeping the conversation alive.
            trace_steps: list[TraceStep] = []
            aspect_hint = {"tipo": "tipos", "mecanismo": "cómo funciona", "historia": "historia", "uso": "para qué se usa", "dato": topic}.get(wanted[0], topic)
            _, fetched_docs, _, _ = self._fetch_evidence(f"{topic} {aspect_hint}", trace_steps)
            if fetched_docs:
                mined = sum(self.graph.ingest_document(doc) for doc in fetched_docs)
                if mined:
                    trace_steps.append(TraceStep("graph.enrich", f"mined {mined} new triple(s) for continuation"))
                passages = self.graph.passages_for(topic, wanted, exclude_aspects=excluded, limit=8)
            if not passages:
                hint = f"No tengo aún aspectos adicionales sobre '{topic}', y no pude refrescarlos en este momento. Preguntame otra cosa."
                record = Expediente(message, "continuation", result=hint, trace=trace_steps, telemetry={"success": False})
                self.assistant.memory.save_episode(record)
                return hint, tuple(asdict(step) for step in trace_steps), {"success": False}
            steps = tuple(asdict(step) for step in trace_steps)
        else:
            steps = ()
        from arca.planner import CONNECTORS

        parts: list[str] = []
        urls: list[str] = []
        new_aspects: list[str] = []
        for position, passage in enumerate(passages[:3]):
            connector = "" if position == 0 else CONNECTORS.get(passage["aspect"], "")
            body = passage["passage"]
            parts.append(body if position == 0 else f"{connector}{body}")
            new_aspects.append(passage["aspect"])
            if passage["source_url"] and passage["source_url"] not in urls:
                urls.append(passage["source_url"])
        text = " ".join(parts)
        self._track_topic(state, [topic], new_aspects)
        step = TraceStep("continuation.graph", f"served aspects {new_aspects} for '{topic}' from local graph", evidence=tuple(urls))
        all_steps = steps + (asdict(step),) if isinstance(steps, tuple) else (asdict(step),)
        record = Expediente(message, "continuation", result=text, trace=[step], telemetry={"success": True})
        self.assistant.memory.save_episode(record)
        return text, all_steps, {"success": True, "sources": len(urls), "evidence_origin": "graph"}

    def _via_assistant(self, query: str) -> tuple[str, tuple[dict[str, Any], ...], dict[str, Any]]:
        result = self.assistant.ask(query)
        expediente = result["expediente"]
        return ResponseQuality.clean(result["answer"], query), tuple(expediente.get("trace", [])), dict(expediente.get("telemetry", {}))

    def _search_results(self, query: str) -> list[Any]:
        try:
            return self.assistant.web.search(query, limit=self.search_limit)
        except Exception as error:
            return []

    def _fetch_evidence(self, query: str, trace_steps: list[TraceStep]) -> tuple[list[str], list[dict[str, Any]], list[tuple[str, str]], bool]:
        """Fetch pages in search-rank order. Also reports alternative senses
        (namesake articles) and whether an exact-title dominant exists."""
        memory = self.assistant.memory
        results = self._search_results(query)[: self.max_web_docs + 2]
        concepts = self._concept_tokens(query)
        dominant = any(self._strict_title(result.title, concepts) for result in results)
        alternatives: list[tuple[str, str]] = []
        seen_titles: set[str] = set()
        saved_urls: list[str] = []
        fetched_docs: list[dict[str, Any]] = []
        fetched_count = 0
        for result in results:
            if "desambiguación" in result.title.casefold():
                continue
            title_matches = _fuzzy_contains(result.title, concepts[0]) if concepts else False
            if title_matches and not self._strict_title(result.title, concepts):
                key = strip_accents(result.title).casefold()
                if key not in seen_titles:
                    seen_titles.add(key)
                    alternatives.append((result.title, result.url))
            if fetched_count >= self.max_web_docs:
                continue
            try:
                if result.text and len(result.text) > 200:
                    title, url, snippet, content = result.title, result.url, result.snippet, result.text
                else:
                    full = self.assistant.web.fetch(result.url)
                    title, url, snippet, content = (result.title or full.title), full.url, full.snippet, full.text
                memory.save_document(title, url, snippet, content, source="web")
                saved_urls.append(url)
                fetched_docs.append({"title": title, "url": url, "snippet": snippet, "content": content})
                fetched_count += 1
            except Exception as error:
                trace_steps.append(TraceStep("web.skip", f"{result.url}: {error}"))
        trace_steps.append(TraceStep("web.fetch", f"fetched {len(saved_urls)} page(s)", evidence=tuple(saved_urls)))
        return saved_urls, fetched_docs, alternatives, dominant

    def _ask_which_sense(self, query: str, senses: list[tuple[str, str]], state: ConversationState, trace_steps: list[TraceStep]) -> tuple[str, tuple[dict[str, Any], ...], dict[str, Any]]:
        keyword = keywords_of(query)
        letters = "abcdef"
        options = []
        for index, (title, _) in enumerate(senses[:4]):
            options.append(f"{letters[index]}) {title}")
        state.pending_senses = [title for title, _ in senses[:4]]
        self.sessions.save(state)
        text = (
            f"Encontré varios sentidos para «{keyword}»:\n"
            + "\n".join(options)
            + "\n\n¿A cuál te referís? Respondé con la letra o el nombre."
        )
        trace_steps.append(TraceStep("disambiguate.clarify", f"{len(options)} senses detected"))
        record = Expediente(query, "disambiguate", result=text, trace=trace_steps, telemetry={"success": True})
        self.assistant.memory.save_episode(record)
        return text, tuple(asdict(step) for step in trace_steps), {"success": True, "senses": len(options)}

    def _resolve_pending_sense(self, message: str, senses: list[str]) -> str | None:
        stripped = message.strip()
        letter = re.fullmatch(r"[¿¡\s]*([a-f])[\s).!?]*", stripped, re.I)
        if letter:
            index = ord(letter.group(1).lower()) - ord("a")
            if 0 <= index < len(senses):
                return senses[index]
        number = re.fullmatch(r"[¿¡\s]*(\d)[\s).!?]*", stripped)
        if number:
            index = int(number.group(1)) - 1
            if 0 <= index < len(senses):
                return senses[index]
        lowered = strip_accents(stripped).casefold()
        best, best_score = None, 0.0
        for title in senses:
            score = SequenceMatcher(None, strip_accents(title).casefold(), lowered).ratio()
            if lowered in strip_accents(title).casefold():
                score = max(score, 0.95)
            if score > best_score:
                best, best_score = title, score
        return best if best_score >= 0.55 else None

    def _accept(self, query: str, text: str, docs: list[dict[str, Any]]) -> tuple[bool, str]:
        if self._on_topic(query, text):
            return True, "ok"
        if _DEFINITION_QUERY.match(query.strip().lstrip("¿¡ \t")) and any(
            self._strict_title(str(doc.get("title", "")), self._concept_tokens(query)) for doc in docs
        ):
            return True, "relaxed_by_title"
        return False, "offtopic"

    @staticmethod
    def _strict_title(title: str, concepts: list[str]) -> bool:
        normalized_title = strip_accents(title).casefold().strip()
        for concept in concepts:
            subject = strip_accents(concept).casefold()
            if normalized_title == subject:
                return True
            if abs(len(normalized_title) - len(subject)) <= 2 and SequenceMatcher(None, normalized_title, subject).ratio() >= 0.92:
                return True
        return False

    @staticmethod
    def _concept_tokens(query: str) -> list[str]:
        return concept_tokens(query)

    @staticmethod
    def _on_topic(query: str, evidence_text: str) -> bool:
        concepts = ARCAAgentBackend._concept_tokens(query)
        if not concepts:
            return True
        body = evidence_text.split("\nFuentes:")[0]
        lines = [line for line in body.splitlines() if line.strip()]
        if not lines:
            return False
        hits = sum(1 for line in lines if _fuzzy_contains(line, concepts[0]))
        if hits / len(lines) < 0.4:
            return False
        lead_line = next((line for line in lines if len(line) > 60), "")
        if _DEFINITION_QUERY.match(query.strip().lstrip("¿¡ \t")):
            cues = (
                " es un ", " es una ", " es el ", " es la ", " es todo ", " es toda ",
                " es cualquier ", " significa", " consiste", " se define", " se denomina",
                " es aquel", " es aquella", " fue un ", " fue una ", " llamado ", " conocida como",
                " plataforma", " herramienta", " sistema", " lenguaje", " paradigma", " concepto",
            )
            subject_pattern = re.compile(rf"\b{re.escape(strip_accents(concepts[0]))}\w*\s+(es|fue|era|significa)\b", re.I)
            if any(all(_fuzzy_contains(line, token) for token in concepts) and any(cue in line.casefold() for cue in cues) for line in lines):
                return True
            if lead_line and all(_fuzzy_contains(lead_line, token) for token in concepts):
                return True
            return False
        if len(concepts) > 1 and not any(_fuzzy_contains(line, concepts[1]) for line in lines):
            return False
        return True

    def _procedure_recall(self, query: str, intent: str) -> tuple[str, tuple[dict[str, Any], ...], dict[str, Any]] | None:
        wants_how = intent in {"planning", "memory_read"} or re.search(r"cómo|como se|pasos|procedimiento", query, re.I)
        if not wants_how:
            return None
        found = self.assistant.memory.find_procedure(query)
        if found is None:
            return None
        self.assistant.memory.record_procedure_use(found["id"], success=True)
        listing = "\n".join(f"{index}. {step}" for index, step in enumerate(found["steps"], start=1))
        text = f"Según mi memoria procedural ({found['name']}, usada {found['uses'] + 1} vez/veces):\n{listing}"
        step_record = TraceStep("procedure.recall", f"recalled stored procedure '{found['name']}'")
        return text, (asdict(step_record),), {"success": True, "procedure": found["name"]}

    def _procedure_teach(self, query: str) -> tuple[str, tuple[dict[str, Any], ...], dict[str, Any]] | None:
        parsed = _parse_procedure_teaching(query)
        if parsed is None:
            return None
        name, steps, triggers = parsed
        try:
            self.assistant.memory.save_procedure(name, triggers, steps, source="user")
        except ValueError as error:
            message = f"No pude guardar el procedimiento: {error}"
            return message, (asdict(TraceStep("procedure.reject", str(error))),), {"success": False}
        listing = "\n".join(f"{index}. {step}" for index, step in enumerate(steps, start=1))
        text = f"Procedimiento '{name}' guardado en memoria permanente:\n{listing}"
        step_record = TraceStep("procedure.save", f"stored procedure '{name}' with {len(steps)} step(s)")
        record = Expediente(query, "procedure_write", result=name, trace=[step_record], telemetry={"success": True})
        self.assistant.memory.save_episode(record)
        return text, (asdict(step_record),), {"success": True, "procedure": name}


def keywords_of(query: str) -> str:
    from arca.web.client import keywords_from

    return keywords_from(query)
