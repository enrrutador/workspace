import tempfile
import unittest
from pathlib import Path

from arca.agent_api import ARCAAgentBackend
from arca.memory import MemoryStore
from arca.native_lm import ARCALanguageModel, ModelConfig


def make_backend(folder: str) -> ARCAAgentBackend:
    model = ARCALanguageModel(ModelConfig(embedding_size=8, hidden_size=12))
    model.train_text("ARCA local model. " * 3, epochs=1)
    model_path = Path(folder) / "model.npz"
    model.save(model_path)
    return ARCAAgentBackend(model_path, Path(folder) / "memory.db")


class ProceduralMemoryTests(unittest.TestCase):
    def test_teach_then_recall_procedure(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = make_backend(folder)
            teach = backend.respond("recuerda el procedimiento desplegar app: 1) compilar el proyecto 2) correr los tests 3) publicar la imagen")
            self.assertTrue(teach.success)
            self.assertIn("desplegar app", teach.text.casefold())
            recall = backend.respond("cómo hago para el procedimiento desplegar app?")
            self.assertIn("compilar", recall.text.casefold())
            self.assertIn("publicar", recall.text.casefold())

    def test_procedure_survives_backend_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            model = ARCALanguageModel(ModelConfig(embedding_size=8, hidden_size=12))
            model.train_text("ARCA local model. " * 3, epochs=1)
            model.save(root / "model.npz")
            first = ARCAAgentBackend(root / "model.npz", root / "memory.db")
            first.respond("recuerda el procedimiento backup diario: 1) exportar base 2) comprimir archivo")
            second = ARCAAgentBackend(root / "model.npz", root / "memory.db")
            answer = second.respond("pasos del procedimiento backup diario")
            self.assertIn("exportar base", answer.text.casefold())


class MemoryRetentionTests(unittest.TestCase):
    def test_document_dedup_and_pruning(self):
        with tempfile.TemporaryDirectory() as folder:
            store = MemoryStore(Path(folder) / "arca.db", max_docs=3)
            for index in range(6):
                store.save_document(f"doc {index}", f"https://example.com/{index}", "snippet", "contenido " * 20)
            stats = store.stats()
            self.assertLessEqual(stats["documents"], 3)

    def test_save_and_find_procedure_directly(self):
        with tempfile.TemporaryDirectory() as folder:
            store = MemoryStore(Path(folder) / "arca.db")
            store.save_procedure("migrar datos", ["migrar", "datos"], ["hacer dump", "restaurar en destino"])
            found = store.find_procedure("necesito migrar datos ya")
            self.assertIsNotNone(found)
            self.assertEqual(found["steps"], ["hacer dump", "restaurar en destino"])
            store.record_procedure_use(found["id"], success=True)
            self.assertEqual(store.list_procedures()[0]["uses"], 1)


class ConceptGateTests(unittest.TestCase):
    def _backend_with_docs(self, folder: str, docs: list[tuple[str, str]]):
        backend = make_backend(folder)
        for url, content in docs:
            backend.assistant.memory.save_document(url.split("/")[-1], url, "snippet", content, source="web")
        backend.assistant.web.search = lambda query, limit=5: []
        return backend

    def test_offtopic_cache_rejected_when_web_down(self):
        rust_doc = ("https://example.com/rust", "Rust es un lenguaje de programación de sistemas compilado y multiparadigma. "
                    "La programación en Rust garantiza seguridad de memoria. Rust admite varios paradigmas.")
        with tempfile.TemporaryDirectory() as folder:
            backend = self._backend_with_docs(folder, [rust_doc])
            result = backend.respond("¿Qué es la programación orientada a objetos?")
            self.assertIn("evidencia", result.text.casefold(), "must not serve Rust doc for POO question")

    def test_matching_cache_served_instantly(self):
        poo_doc = ("https://example.com/poo", "La programación orientada a objetos es un paradigma de programación. "
                   "La programación orientada a objetos organiza el código en clases y objetos que combinan datos y comportamiento. "
                   "Este paradigma facilita la reutilización mediante herencia y polimorfismo.")
        with tempfile.TemporaryDirectory() as folder:
            backend = self._backend_with_docs(folder, [poo_doc])
            result = backend.respond("¿Qué es la programación orientada a objetos?")
            self.assertTrue(result.success)
            self.assertEqual(result.telemetry.get("evidence_origin"), "memory")
            self.assertIn("paradigma", result.text.casefold())

    def test_single_concept_still_works(self):
        docker_doc = ("https://example.com/docker", "Docker es una plataforma de contenedores que empaqueta aplicaciones con sus dependencias. "
                      "Docker permite desplegar software de forma consistente en cualquier entorno.")
        with tempfile.TemporaryDirectory() as folder:
            backend = self._backend_with_docs(folder, [docker_doc])
            result = backend.respond("¿Qué es Docker?")
            self.assertIn("contenedor", result.text.casefold())


class ProseQualityTests(unittest.TestCase):
    def test_comment_and_menu_noise_filtered(self):
        from arca.retrieval import split_sentences
        content = (
            "Un barco es un vehículo que se desplaza sobre el agua mediante flotación. "
            "Nora de Vita dice: 27 diciembre, 2023 a las 11:40 pm Gente programadora, no funcionan los íconos. Responder "
            "Cómo funciona YouTube IA Derechos de autor Economía de creadores Elecciones Niños Privacidad Noticias. "
            "El casco de un barco se fabrica en una sola pieza si es pequeño."
        )
        sentences = split_sentences(content)
        joined = " ".join(sentences).casefold()
        self.assertNotIn("dice:", joined)
        self.assertNotIn("derechos de autor", joined)
        self.assertIn("flotación", joined)

    def test_prose_has_no_bullets(self):
        from arca.retrieval import compose_prose
        docs = [{"title": "barco", "url": "https://x.com/barco", "content": "Un barco es un vehículo capaz de flotar en el agua y trasladarse sobre ella. Los barcos modernos usan tecnología para ser más seguros. El casco se fabrica en piezas según el tamaño del buque."}]
        result = compose_prose("¿Qué es un barco?", docs)
        self.assertIsNotNone(result)
        text = result[0]
        self.assertFalse(text.lstrip().startswith("-"))
        self.assertTrue(text.split("\n")[0].count(". ") >= 1, "should be flowing prose, not single fragment")

    def test_typo_tolerated_in_concept_gate(self):
        from arca.agent_api import ARCAAgentBackend
        evidence = "Una infografía tridimensional es una representación visual de datos con profundidad y volumen. Combina diseño gráfico con modelos en 3D para comunicar información compleja de manera clara."
        self.assertTrue(ARCAAgentBackend._on_topic("¿Qué es una infografía tridimencional?", evidence))
        off_topic = "Los barcos navegan por el mar transportando carga entre puertos comerciales."
        self.assertFalse(ARCAAgentBackend._on_topic("¿Qué es una infografía tridimencional?", off_topic))


class InternalMetaPromptTests(unittest.TestCase):
    STATE_PROMPT = (
        "Track the current state of the session.\n\n"
        "Objective\nEl usuario está preguntando qué es Rust.\n"
        "Important Details\n(none)\n"
        "Work State\nCompleted\n"
        "Active Tasks\n(none)\n"
        "Blocked\n(none)\n"
        "Next Move\n(none)\n"
        "Relevant Files\n(none)"
    )

    def test_state_template_gets_deterministic_reply(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = make_backend(folder)
            before = backend.assistant.memory.stats()
            result = backend.respond(self.STATE_PROMPT)
            self.assertIn("Objective", result.text)
            self.assertIn("preguntando qué es Rust", result.text)
            self.assertEqual(result.telemetry.get("internal"), "state")
            after = backend.assistant.memory.stats()
            self.assertEqual(before["episodes"], after["episodes"], "meta prompts must not pollute memory")

    def test_title_prompt_returns_short_title(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = make_backend(folder)
            prompt = "The user is chatting. Generate a short title for this conversation. Context: hablamos sobre el procedimiento publicar arca y sus pasos."
            result = backend.respond(prompt)
            self.assertLess(len(result.text), 120)
            self.assertEqual(result.telemetry.get("internal"), "title")

    def test_normal_message_not_caught_by_meta_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = make_backend(folder)
            result = backend.respond("hola, quiero saber sobre objective-c versus work state tools")
            self.assertNotEqual(result.telemetry.get("intent"), "internal_meta")


if __name__ == "__main__":
    unittest.main()
