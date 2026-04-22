"""Tests for Loveline debug language-model setup routing."""

from absl.testing import absltest

from examples.loveline_debug import language_model_setup


class LanguageModelSetupTest(absltest.TestCase):

  def test_ollama_uses_loveline_shim(self):
    calls = []

    class FakeLovelineOllama:

      def __init__(self, **kwargs):
        calls.append(kwargs)

    original_cls = language_model_setup.ollama_shim.LovelineOllamaLanguageModel
    language_model_setup.ollama_shim.LovelineOllamaLanguageModel = (
        FakeLovelineOllama
    )
    try:
      model = language_model_setup.setup(
          api_type="ollama",
          model_name="qwen3.5:35b-a3b",
          disable_language_model=False,
      )
    finally:
      language_model_setup.ollama_shim.LovelineOllamaLanguageModel = (
          original_cls
      )

    self.assertIsInstance(model, FakeLovelineOllama)
    self.assertEqual(calls, [{"model_name": "qwen3.5:35b-a3b"}])

  def test_non_ollama_uses_stock_concordia_setup(self):
    calls = []

    def fake_stock_setup(**kwargs):
      calls.append(kwargs)
      return "stock-model"

    original_setup = language_model_setup.language_models.language_model_setup
    language_model_setup.language_models.language_model_setup = fake_stock_setup
    try:
      model = language_model_setup.setup(
          api_type="openai",
          model_name="gpt-test",
          api_key="key",
          disable_language_model=False,
      )
    finally:
      language_model_setup.language_models.language_model_setup = original_setup

    self.assertEqual(model, "stock-model")
    self.assertEqual(
        calls,
        [{
            "api_type": "openai",
            "model_name": "gpt-test",
            "api_key": "key",
            "disable_language_model": False,
        }],
    )


if __name__ == "__main__":
  absltest.main()
