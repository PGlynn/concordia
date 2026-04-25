"""Tests for the Loveline-local Codex OAuth shim."""

from __future__ import annotations

import tempfile
from types import SimpleNamespace

from absl.testing import absltest

from concordia.language_model import language_model
from examples.loveline_debug import codex_oauth_shim


class FakeSubprocessModule:

  def __init__(self, *, stdout: str = "", returncode: int = 0):
    self.stdout = stdout
    self.returncode = returncode
    self.calls = []
    self._written_output = ""
    self.raise_timeout = False

  def set_output(self, output: str) -> None:
    self._written_output = output

  def run(self, command, **kwargs):
    self.calls.append({"command": command, **kwargs})
    if self.raise_timeout:
      raise codex_oauth_shim.subprocess.TimeoutExpired(command, kwargs["timeout"])
    output_flag = command.index("--output-last-message") + 1
    with open(command[output_flag], "w", encoding="utf-8") as handle:
      handle.write(self._written_output)
    return SimpleNamespace(
        returncode=self.returncode,
        stdout=self.stdout,
        stderr="boom" if self.returncode else "",
    )


class CodexOauthShimTest(absltest.TestCase):

  def test_sample_text_builds_safe_codex_exec_command_and_reads_last_message(self):
    fake_subprocess = FakeSubprocessModule()
    fake_subprocess.set_output('"Answer: done"\n')
    model = codex_oauth_shim.LovelineCodexOAuthLanguageModel(
        model_name="gpt-5.4",
        subprocess_module=fake_subprocess,
        working_directory="/tmp/loveline_debug",
    )

    result = model.sample_text(
        "Alex says",
        terminators=["\nSTOP"],
        timeout=12,
    )

    self.assertEqual(result, "done")
    self.assertLen(fake_subprocess.calls, 1)
    call = fake_subprocess.calls[0]
    self.assertEqual(
        call["command"][:10],
        [
            "codex",
            "exec",
            "--model",
            "gpt-5.4",
            "--skip-git-repo-check",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "--color",
            "never",
        ],
    )
    self.assertIn("--output-last-message", call["command"])
    self.assertEqual(
        call["command"][-3:],
        ["--cd", "/tmp/loveline_debug", "-"],
    )
    self.assertEqual(call["cwd"], "/tmp/loveline_debug")
    self.assertEqual(call["timeout"], 12.0)
    self.assertTrue(call["capture_output"])
    self.assertTrue(call["text"])
    self.assertIn("Return only the answer text.", call["input"])
    self.assertIn("Stop before emitting any of these terminators", call["input"])

  def test_sample_choice_parses_json_choice_from_codex_output(self):
    fake_subprocess = FakeSubprocessModule()
    fake_subprocess.set_output('{"choice": 2}')
    model = codex_oauth_shim.LovelineCodexOAuthLanguageModel(
        model_name="gpt-5.4",
        subprocess_module=fake_subprocess,
        working_directory=tempfile.gettempdir(),
    )

    idx, response, debug = model.sample_choice(
        "Choose a date location",
        ["Beach", "Cafe"],
    )

    self.assertEqual((idx, response), (1, "Cafe"))
    self.assertEqual(debug, {"raw": '{"choice": 2}'})
    self.assertIn('Return JSON only in the form {"choice": <number>}.', fake_subprocess.calls[0]["input"])

  def test_sample_text_translates_cli_timeout(self):
    fake_subprocess = FakeSubprocessModule()
    fake_subprocess.raise_timeout = True
    model = codex_oauth_shim.LovelineCodexOAuthLanguageModel(
        model_name="gpt-5.4",
        subprocess_module=fake_subprocess,
    )

    with self.assertRaisesRegex(TimeoutError, "timed out after 3.0s"):
      model.sample_text("Hi", timeout=3)

  def test_sample_choice_raises_invalid_response_after_retries(self):
    fake_subprocess = FakeSubprocessModule()
    fake_subprocess.set_output("not json")
    model = codex_oauth_shim.LovelineCodexOAuthLanguageModel(
        model_name="gpt-5.4",
        subprocess_module=fake_subprocess,
    )

    with self.assertRaises(language_model.InvalidResponseError):
      model.sample_choice("Choose", ["A", "B"])

    self.assertLen(
        fake_subprocess.calls,
        codex_oauth_shim._MAX_MULTIPLE_CHOICE_ATTEMPTS,
    )
