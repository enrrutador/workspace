import unittest

from arca.web import WebEvidenceClient, keywords_from


class KeywordsTests(unittest.TestCase):
    def test_strips_question_wrappers(self):
        self.assertEqual(keywords_from("¿Qué es un barco?"), "barco")
        self.assertEqual(keywords_from("¿Qué es la programación orientada a objetos?"), "programación orientada a objetos")
        self.assertEqual(keywords_from("¿Cómo funciona YouTube?"), "YouTube")
        self.assertEqual(keywords_from("que es una infografia tridimencional"), "infografia tridimencional")

    def test_plain_query_untouched(self):
        self.assertEqual(keywords_from("Kubernetes deployment"), "Kubernetes deployment")


class MergedSearchTests(unittest.TestCase):
    def test_summary_source_not_dropped(self):
        """Regression: a signature mismatch made search() silently drop the
        summary source, so definitional answers lost their lead definition."""
        client = WebEvidenceClient(max_bytes=500_000)
        try:
            results = client.search("¿Qué es un barco?", limit=5)
        except OSError:
            self.skipTest("sin red")
        if not results:
            self.skipTest("todos los motores limitados/desconectados en este momento")
        self.assertTrue(results)
        summaries = [r for r in results if r.source == "wikipedia-summary"]
        self.assertTrue(summaries, "wikipedia-summary debe estar presente, no fue descartado")
        self.assertGreater(len(summaries[0].text), 80)


if __name__ == "__main__":
    unittest.main()
