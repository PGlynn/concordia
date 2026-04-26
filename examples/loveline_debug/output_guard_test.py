"""Tests for the Loveline-local spoken output verifier and scheduler."""

from __future__ import annotations

from absl.testing import absltest

from concordia.language_model import language_model
from examples.loveline_debug import output_guard


def _spoken_prompt(question: str) -> str:
  return (
      "Instructions\n"
      "For free-action dialogue, respond only with the exact spoken words "
      "the character says in first person. Do not narrate actions.\n"
      f"Question: {question}\n"
      "Answer: "
  )


class _FakeModel(language_model.LanguageModel):

  def __init__(self, responses: list[str]):
    self._responses = list(responses)
    self.calls = []

  def sample_text(self, prompt: str, **kwargs) -> str:
    self.calls.append({"prompt": prompt, **kwargs})
    return self._responses.pop(0)

  def sample_choice(self, prompt, responses, *, seed=None):
    del prompt, responses, seed
    raise AssertionError("sample_choice should not be used in this test")


class OutputGuardTest(absltest.TestCase):

  def test_retries_banned_terms_and_injects_turn_topic(self):
    model = _FakeModel([
        "I want something quiet and safe.",
        "I like how direct you are.",
    ])
    wrapped = output_guard.SpokenOutputGuard(
        model,
        output_guard.SpokenOutputGuardConfig(
            enabled=True,
            banned_terms=("quiet", "safe"),
            max_retries=1,
            topic_schedule=("ask about family", "ask about work",),
        ),
    )

    result = wrapped.sample_text(_spoken_prompt("Say one spoken reply."), seed=9)

    self.assertEqual(result, "I like how direct you are.")
    self.assertLen(model.calls, 2)
    self.assertIn("Turn topic focus: ask about family.", model.calls[0]["prompt"])
    self.assertEqual(model.calls[0]["seed"], 9)
    self.assertEqual(model.calls[1]["seed"], 10)
    self.assertIn(
        "Previous invalid attempt: 'I want something quiet and safe.'.",
        model.calls[1]["prompt"],
    )
    self.assertIn("banned terms: quiet, safe.", model.calls[1]["prompt"])

  def test_scheduler_advances_only_for_spoken_actor_turns(self):
    model = _FakeModel([
        "First clean line.",
        "Reflection text.",
        "Second clean line.",
    ])
    wrapped = output_guard.SpokenOutputGuard(
        model,
        output_guard.SpokenOutputGuardConfig(
            enabled=True,
            topic_schedule=("topic one", "topic two"),
        ),
    )

    wrapped.sample_text(_spoken_prompt("Say one spoken reply."))
    wrapped.sample_text(
        _spoken_prompt("What kind of person is Alex right now?")
    )
    wrapped.sample_text(_spoken_prompt("Answer Blake with one spoken line."))

    self.assertIn("Turn topic focus: topic one.", model.calls[0]["prompt"])
    self.assertNotIn("Turn topic focus:", model.calls[1]["prompt"])
    self.assertIn("Turn topic focus: topic two.", model.calls[2]["prompt"])

  def test_exhausted_retries_raise_invalid_response_when_enforcing(self):
    model = _FakeModel(["Alex: (smiles) I feel safe here.", "Narration: quiet."])
    wrapped = output_guard.SpokenOutputGuard(
        model,
        output_guard.SpokenOutputGuardConfig(
            enabled=True,
            banned_terms=("quiet", "feel", "safe"),
            max_retries=1,
        ),
    )

    with self.assertRaises(language_model.InvalidResponseError):
      wrapped.sample_text(_spoken_prompt("Reply with one line."))


if __name__ == "__main__":
  absltest.main()
