"""Tests for the Loveline-specific Ollama shim."""

from absl.testing import absltest

from examples.loveline_debug import ollama_shim


class FakeOllamaClient:

  def __init__(self, responses):
    self._responses = list(responses)
    self.calls = []

  def generate(self, **kwargs):
    self.calls.append(kwargs)
    return {"response": self._responses.pop(0)}


class OllamaShimTest(absltest.TestCase):

  def test_sample_text_sends_loveline_ollama_controls(self):
    client = FakeOllamaClient(['"Answer: done"'])
    model = ollama_shim.LovelineOllamaLanguageModel(
        model_name="qwen3.5:35b-a3b", client=client
    )

    result = model.sample_text(
        "Alex says",
        max_tokens=123,
        terminators=["\nSTOP"],
        temperature=0.25,
        top_p=0.75,
        top_k=20,
        seed=7,
    )

    self.assertEqual(result, "done")
    self.assertLen(client.calls, 1)
    call = client.calls[0]
    self.assertEqual(call["model"], "qwen3.5:35b-a3b")
    self.assertIn("Alex says", call["prompt"])
    self.assertEqual(call["keep_alive"], "10m")
    self.assertIs(call["think"], False)
    self.assertEqual(
        call["options"],
        {
            "stop": ["\nSTOP"],
            "temperature": 0.25,
            "top_p": 0.75,
            "top_k": 20,
            "num_predict": 123,
            "seed": 7,
        },
    )

  def test_sample_text_strips_answer_label_before_continuation_prefix(self):
    client = FakeOllamaClient(['"Answer: Jake is not a turtle."'])
    model = ollama_shim.LovelineOllamaLanguageModel(
        model_name="qwen3.5:35b-a3b", client=client
    )

    result = model.sample_text("Question: Is Jake a turtle?\nAnswer: Jake is ")

    self.assertEqual(result, "not a turtle.")
    self.assertIn(
        "Existing answer text: 'Jake is'", client.calls[0]["prompt"]
    )

  def test_sample_choice_sends_think_false_and_json_format(self):
    client = FakeOllamaClient(['{"choice": "2"}'])
    model = ollama_shim.LovelineOllamaLanguageModel(
        model_name="qwen3.5:35b-a3b", client=client
    )

    idx, response, debug = model.sample_choice(
        "Choose a date location", ["A", "B"], seed=11
    )

    self.assertEqual(idx, 1)
    self.assertEqual(response, "B")
    self.assertEqual(debug, {"raw": '{"choice": "2"}'})
    self.assertLen(client.calls, 1)
    call = client.calls[0]
    self.assertEqual(call["format"], "json")
    self.assertEqual(call["keep_alive"], "10m")
    self.assertIs(call["think"], False)
    self.assertEqual(
        call["options"],
        {
            "stop": [],
            "temperature": 0.0,
            "top_p": 0.9,
            "top_k": 40,
            "num_predict": 64,
            "seed": 11,
        },
    )


if __name__ == "__main__":
  absltest.main()
