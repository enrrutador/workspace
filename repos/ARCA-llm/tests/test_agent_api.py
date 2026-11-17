import tempfile
import unittest
from pathlib import Path

from arca.agent_api import ARCAAgentBackend
from arca.native_lm import ARCALanguageModel, ModelConfig


def make_backend(folder: str) -> tuple[ARCAAgentBackend, Path]:
    model = ARCALanguageModel(ModelConfig(embedding_size=8, hidden_size=12))
    model.train_text("ARCA local model. " * 3, epochs=1)
    model_path = Path(folder) / "model.npz"
    model.save(model_path)
    return ARCAAgentBackend(model_path, Path(folder) / "memory.db"), model_path


class AgentAPITests(unittest.TestCase):
    def test_backend_responds_with_trace(self):
        with tempfile.TemporaryDirectory() as folder:
            backend, _ = make_backend(folder)
            result = backend.respond("hola")
            self.assertTrue(result.success)
            self.assertTrue(result.text)
            self.assertTrue(result.trace)

    def test_unknown_question_is_honest(self):
        with tempfile.TemporaryDirectory() as folder:
            backend, _ = make_backend(folder)
            result = backend.respond("zzqqvx florbinator qwuxlarp zzzblorp")
            self.assertIn("evidencia", result.text.casefold())

    def test_remember_and_recall_assertion(self):
        with tempfile.TemporaryDirectory() as folder:
            backend, _ = make_backend(folder)
            backend.respond("remember that the project is ARCA")
            answer = backend.respond("what is the project?")
            self.assertIn("arca", answer.text.casefold())


if __name__ == "__main__":
    unittest.main()
