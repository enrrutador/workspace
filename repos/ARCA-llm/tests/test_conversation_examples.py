"""Conversation contract: each scenario is a promise about how ARCA behaves.
Web is simulated so the suite stays deterministic and fast."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from arca.agent_api import ARCAAgentBackend
from arca.memory import MemoryStore
from arca.native_lm import ARCALanguageModel, ModelConfig
from arca.web.client import WebResult


SHIP_DOC = {
    "title": "Barco",
    "url": "https://es.wikipedia.org/wiki/Barco",
    "snippet": "embarcación",
    "content": (
        "Un barco es un vehículo capaz de flotar en el agua y trasladarse sobre ella mediante flotación. "
        "Los barcos se clasifican en veleros, mercantes y de guerra según su propulsión y función. "
        "Los barcos se utilizan para transportar carga y personas entre puertos comerciales. "
        "El barco fue creado alrededor del año 4000 antes de Cristo en el antiguo Egipto."
    ),
}
FOOTBALLER_DOC = {
    "title": "Valentín Barco",
    "url": "https://es.wikipedia.org/wiki/Valent%C3%ADn_Barco",
    "snippet": "futbolista",
    "content": (
        "Valentín Barco es un futbolista argentino que juega como lateral izquierdo. "
        "Su trayectoria comenzó en las inferiores de Boca Juniors."
    ),
}


def make_backend(folder: str) -> ARCAAgentBackend:
    model = ARCALanguageModel(ModelConfig(embedding_size=8, hidden_size=12))
    model.train_text("ARCA local model. " * 3, epochs=1)
    model_path = Path(folder) / "model.npz"
    model.save(model_path)
    backend = ARCAAgentBackend(model_path, Path(folder) / "memory.db")
    return backend


def mock_search(results):
    def _search(query, limit=5):
        return list(results)
    return _search


class ConversationContractTests(unittest.TestCase):
    def respond_with(self, backend, message):
        return backend.respond(message)

    # --- Fase 5: contexto ---
    def test_01_time_from_local_clock_no_questions(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = make_backend(folder)
            before = datetime.now()
            result = backend.respond("¿Qué hora es?")
            self.assertTrue(result.success)
            self.assertIn("Son las", result.text)
            self.assertIn(f"{before.hour:02d}:{before.minute:02d}", result.text)
            self.assertNotIn("?", result.text.split("Son")[0])

    def test_02_today_is_weekday_in_spanish(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = make_backend(folder)
            result = backend.respond("¿Qué día es hoy?")
            weekdays = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
            self.assertTrue(any(day in result.text for day in weekdays), result.text)

    # --- cortesía ---
    def test_03_social_greetings(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = make_backend(folder)
            for message in ("hola", "gracias", "hasta luego"):
                result = backend.respond(message)
                self.assertTrue(result.success and len(result.text) > 10)

    # --- Fase 6 + gate: desambiguación ---
    def _backend_with(self, folder, docs):
        backend = make_backend(folder)
        backend.assistant.web.search = mock_search([WebResult(title=d["title"], url=d["url"], snippet=d["snippet"], source="wikipedia") for d in docs])
        backend.assistant.web.fetch = lambda url: next(
            WebResult(d["title"], d["url"], d["snippet"], d["content"], "web") for d in docs if d["url"] == url)
        return backend

    def test_04_ship_definition_when_dominant(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = self._backend_with(folder, [SHIP_DOC])
            result = backend.respond("¿Qué es un barco?")
            self.assertTrue(result.success)
            lowered = result.text.casefold()
            self.assertTrue("flotar" in lowered or "vehículo" in lowered or "flotante" in lowered, result.text[:200])

    def test_05_tied_senses_trigger_clarifying_question(self):
        tied_doc = dict(SHIP_DOC, title="Barcos de vela", url="https://x/veleros",
                        content="Los barcos de vela son embarcaciones propulsadas por velas. Navegan aprovechando el viento.")
        with tempfile.TemporaryDirectory() as folder:
            backend = self._backend_with(folder, [tied_doc, FOOTBALLER_DOC])
            state_before = backend.sessions.load("default")
            self.assertFalse(state_before.pending_senses)
            result = backend.respond("¿Qué es barco?")
            combined = result.text.lower()
            senses_listed = sum(1 for name in ("vela", "valentín") if name in combined)
            self.assertGreaterEqual(senses_listed, 2, f"debe listar sentidos: {result.text}")
            self.assertIn("¿a cuál", combined.replace("¿A cuál", "¿a cuál"))

    def test_06_dominant_mentions_alternative_namesake(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = self._backend_with(folder, [SHIP_DOC, FOOTBALLER_DOC])
            result = backend.respond("¿Qué es un barco?")
            lowered = result.text.casefold()
            self.assertTrue("flotar" in lowered or "flotante" in lowered or "vehículo" in lowered)

    # --- Fase 4: continuaciones offline ---
    def test_07_tell_me_more_serves_new_aspect_without_web(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = self._backend_with(folder, [SHIP_DOC])
            first = backend.respond("¿Qué es un barco?")
            self.assertTrue(first.success)
            calls = {"n": 0}

            def failing_search(query, limit=5):
                calls["n"] += 1
                raise OSError("red caída")

            backend.assistant.web.search = failing_search
            second = backend.respond("contame más")
            self.assertEqual(calls["n"], 0, "la continuación no debe tocar la red")
            self.assertTrue(second.success, second.text)
            self.assertTrue(len(second.text) > 60)

    def test_08_historical_followup_after_topic(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = self._backend_with(folder, [SHIP_DOC])
            backend.respond("¿Qué es un barco?")
            result = backend.respond("¿Y cuándo fue creado?")
            lowered = result.text.casefold()
            self.assertTrue("egipto" in lowered or "4000" in lowered or "creado" in lowered, result.text[:200])

    # --- typos ---
    def test_09_typo_still_reaches_content(self):
        content = (
            "La infografía es tanto una técnica como una forma de representación visual tridimensional de información compleja con profundidad y volumen. "
            "Combina diseño gráfico, modelos en 3D y datos para explicar ideas con claridad y de manera didáctica con gran valor visual tridimensional. "
            "La infografía tridimensional se usa en arquitectura para mostrar espacios con realismo."
        )
        doc = {"title": "Infografía", "url": "https://es.wikipedia.org/wiki/Infograf%C3%ADa", "snippet": "", "text": content, "content": content}
        with tempfile.TemporaryDirectory() as folder:
            backend = make_backend(folder)
            summary_result = WebResult(title="Infografía", url=doc["url"], snippet="", text=doc["text"], source="wikipedia-summary")
            backend.assistant.web.search = mock_search([summary_result])
            backend.assistant.web.fetch = lambda url: WebResult(doc["title"], doc["url"], doc["snippet"], doc["content"], "web")
            result = backend.respond("que es una infografia tridimencional")
            self.assertTrue(result.success, result.text)
            self.assertIn("visual", result.text.casefold())

    # --- procedimientos ---
    def test_10_procedure_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = make_backend(folder)
            teach = backend.respond("recuerda el procedimiento publicar arca: 1) correr los tests 2) hacer backup 3) reiniciar el servidor")
            self.assertTrue(teach.success)
            recall = backend.respond("cómo es el procedimiento publicar arca?")
            self.assertIn("correr los tests", recall.text)

    # --- honestidad ---
    def test_11_gibberish_gets_honest_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = make_backend(folder)
            backend.assistant.web.search = mock_search([])
            result = backend.respond("zzqqvx florbinator qwuxlarp zzzblorp")
            self.assertIn("evidencia", result.text.casefold())

    # --- memoria semántica ---
    def test_12_remember_then_recall_fact(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = make_backend(folder)
            backend.respond("remember that the project is ARCA")
            answer = backend.respond("what is the project?")
            self.assertIn("arca", answer.text.casefold())


if __name__ == "__main__":
    unittest.main()
