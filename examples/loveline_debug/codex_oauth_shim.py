"""Loveline-local Codex OAuth language-model adapter for debug runs."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Protocol, override

from concordia.language_model import language_model

from examples.loveline_debug import ollama_shim


_MAX_MULTIPLE_CHOICE_ATTEMPTS = 4


class _SubprocessModule(Protocol):

  def run(self, *args: Any, **kwargs: Any) -> Any:
    ...


class LovelineCodexOAuthLanguageModel(language_model.LanguageModel):
  """Uses the server's existing Codex CLI OAuth session for Loveline runs."""

  def __init__(
      self,
      model_name: str,
      *,
      system_message: str = ollama_shim._DEFAULT_SYSTEM_MESSAGE,
      working_directory: str | os.PathLike[str] | None = None,
      subprocess_module: _SubprocessModule = subprocess,
      temporary_directory: type[tempfile.TemporaryDirectory[str]] = (
          tempfile.TemporaryDirectory
      ),
  ) -> None:
    self._model_name = model_name
    self._system_message = system_message
    self._working_directory = Path(
        working_directory if working_directory is not None else Path.cwd()
    )
    self._subprocess = subprocess_module
    self._temporary_directory = temporary_directory

  @override
  def sample_text(
      self,
      prompt: str,
      *,
      max_tokens: int = language_model.DEFAULT_MAX_TOKENS,
      terminators: Collection[str] = language_model.DEFAULT_TERMINATORS,
      temperature: float = language_model.DEFAULT_TEMPERATURE,
      top_p: float = language_model.DEFAULT_TOP_P,
      top_k: int = language_model.DEFAULT_TOP_K,
      timeout: float = language_model.DEFAULT_TIMEOUT_SECONDS,
      seed: int | None = None,
  ) -> str:
    del max_tokens, temperature, top_p, top_k, seed

    continuation_prefix = ollama_shim._extract_continuation_prefix(prompt)
    request = ollama_shim._build_generation_prompt(
        system_message=self._system_message,
        prompt=prompt,
        continuation_prefix=continuation_prefix,
    )
    if terminators:
      request += (
          "\n\nStop before emitting any of these terminators: "
          + ", ".join(repr(item) for item in terminators)
          + "."
      )
    request += "\n\nReturn only the answer text."
    result = self._run_codex_prompt(request, timeout=timeout)
    cleaned = ollama_shim._clean_sample_text(result, continuation_prefix)
    return _truncate_at_terminators(cleaned, terminators)

  @override
  def sample_choice(
      self,
      prompt: str,
      responses: Sequence[str],
      *,
      seed: int | None = None,
  ) -> tuple[int, str, Mapping[str, Any]]:
    del seed
    if not responses:
      raise ValueError("responses must not be empty")

    numbered_options = {
        str(index + 1): response for index, response in enumerate(responses)
    }
    choice_block = "\n".join(
        f"{index}. {response}" for index, response in numbered_options.items()
    )
    request = (
        f"{self._system_message}\n\n"
        f"{prompt}\n\n"
        "Choose exactly one option from the list below.\n"
        'Return JSON only in the form {"choice": <number>}.\n'
        f"Valid numbers: {', '.join(numbered_options.keys())}.\n\n"
        f"Options:\n{choice_block}"
    )

    last_raw = ""
    for attempt in range(_MAX_MULTIPLE_CHOICE_ATTEMPTS):
      prompt_text = request
      if attempt:
        prompt_text += (
            "\n\nYour previous response was invalid for this parser: "
            f"{last_raw!r}\nReturn valid JSON only."
        )
      last_raw = self._run_codex_prompt(
          prompt_text,
          timeout=language_model.DEFAULT_TIMEOUT_SECONDS,
      ).strip()
      parsed_choice = ollama_shim._extract_choice(last_raw, responses)
      if parsed_choice is None:
        continue
      if parsed_choice in numbered_options:
        idx = int(parsed_choice) - 1
        return idx, responses[idx], {"raw": last_raw}
      normalized = ollama_shim._normalize(parsed_choice)
      for idx, candidate in enumerate(responses):
        if normalized == ollama_shim._normalize(candidate):
          return idx, candidate, {"raw": last_raw}

    raise language_model.InvalidResponseError(
        f"Too many multiple choice attempts. Last attempt: {last_raw!r}"
    )

  def _run_codex_prompt(self, prompt: str, *, timeout: float) -> str:
    try:
      with self._temporary_directory(prefix="loveline_codex_oauth_") as tmp_dir:
        output_path = Path(tmp_dir) / "last_message.txt"
        command = self._build_command(output_path)
        completed = self._subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            cwd=str(self._working_directory),
            timeout=max(float(timeout), 1.0),
            check=False,
        )
        if completed.returncode != 0:
          raise RuntimeError(_codex_exec_failure(command, completed))
        if output_path.exists():
          result = output_path.read_text(encoding="utf-8").strip()
          if result:
            return result
        fallback = (completed.stdout or "").strip()
        if fallback:
          return fallback
        raise RuntimeError(
            "Codex OAuth request finished without a final message."
        )
    except subprocess.TimeoutExpired as exc:
      raise TimeoutError(
          f"Codex OAuth request timed out after {float(timeout):.1f}s."
      ) from exc

  def _build_command(self, output_path: Path) -> list[str]:
    return [
        "codex",
        "exec",
        "--model",
        self._model_name,
        "--skip-git-repo-check",
        "--ephemeral",
        "--sandbox",
        "read-only",
        "--color",
        "never",
        "--output-last-message",
        str(output_path),
        "--cd",
        str(self._working_directory),
        "-",
    ]


def _codex_exec_failure(command: Sequence[str], completed: Any) -> str:
  del command
  stderr = str(getattr(completed, "stderr", "") or "").strip()
  stdout = str(getattr(completed, "stdout", "") or "").strip()
  details = stderr or stdout or "no CLI output"
  return (
      "Codex OAuth request failed with exit code "
      f"{getattr(completed, 'returncode', '?')}: {details}"
  )


def _truncate_at_terminators(
    text: str,
    terminators: Collection[str],
) -> str:
  truncated = text
  for terminator in terminators:
    if not terminator:
      continue
    index = truncated.find(terminator)
    if index >= 0:
      truncated = truncated[:index]
  return truncated.strip()
