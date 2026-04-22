"""Loveline-specific Ollama language model for the debug UI."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
import importlib
import json
import re
from typing import Any, override

from concordia.language_model import language_model
from concordia.utils import measurements as measurements_lib


_MAX_MULTIPLE_CHOICE_ATTEMPTS = 8
_DEFAULT_TEMPERATURE = 0.5
_DEFAULT_TERMINATORS = ()
_DEFAULT_KEEP_ALIVE = "10m"
_DEFAULT_SYSTEM_MESSAGE = (
    "You are simulating characters and game-master decisions inside Concordia. "
    "Respond directly to the prompt with in-world content only. For free-form "
    "actions, produce a natural utterance or action, not analysis or meta "
    "commentary. Do not repeat the speaker's name unless the prompt explicitly "
    "asks for it. Do not wrap free-form answers in quotation marks unless the "
    "prompt explicitly asks for quoted text. When the prompt asks you to "
    "choose from listed options, pick exactly one valid option and follow the "
    "requested format exactly."
)


class LovelineOllamaLanguageModel(language_model.LanguageModel):
  """Narrow Ollama adapter matching Loveline local debugging behavior."""

  def __init__(
      self,
      model_name: str,
      *,
      system_message: str = _DEFAULT_SYSTEM_MESSAGE,
      measurements: measurements_lib.Measurements | None = None,
      channel: str = language_model.DEFAULT_STATS_CHANNEL,
      client: Any | None = None,
  ) -> None:
    self._model_name = model_name
    self._system_message = system_message
    self._terminators = []
    self._client = client if client is not None else _create_ollama_client()
    self._measurements = measurements
    self._channel = channel

  @override
  def sample_text(
      self,
      prompt: str,
      *,
      max_tokens: int = language_model.DEFAULT_MAX_TOKENS,
      terminators: Collection[str] = _DEFAULT_TERMINATORS,
      temperature: float = _DEFAULT_TEMPERATURE,
      top_p: float = language_model.DEFAULT_TOP_P,
      top_k: int = language_model.DEFAULT_TOP_K,
      timeout: float = language_model.DEFAULT_TIMEOUT_SECONDS,
      seed: int | None = None,
  ) -> str:
    del timeout  # Ollama's Python client accepts timeout at client creation.

    continuation_prefix = _extract_continuation_prefix(prompt)
    prompt_to_send = _build_generation_prompt(
        system_message=self._system_message,
        prompt=prompt,
        continuation_prefix=continuation_prefix,
    )
    options = _request_options(
        stop=self._terminators + list(terminators),
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        max_tokens=max_tokens,
        seed=seed,
    )

    last_cleaned = ""
    result = ""
    for _ in range(4):
      response = self._client.generate(
          model=self._model_name,
          prompt=prompt_to_send,
          options=options,
          keep_alive=_DEFAULT_KEEP_ALIVE,
          think=False,
      )
      result = response["response"].strip()
      cleaned = _clean_sample_text(result, continuation_prefix)
      last_cleaned = cleaned
      if cleaned and not _contains_forbidden_stage_direction(cleaned):
        result = cleaned
        break
      options["temperature"] = max(0.2, float(options["temperature"]))
    else:
      result = last_cleaned or result

    if self._measurements is not None:
      self._measurements.publish_datum(
          self._channel, {"raw_text_length": len(result)}
      )
    return result

  @override
  def sample_choice(
      self,
      prompt: str,
      responses: Sequence[str],
      *,
      seed: int | None = None,
  ) -> tuple[int, str, Mapping[str, Any]]:
    if not responses:
      raise ValueError("responses must not be empty")

    numbered_options = {
        str(index + 1): response for index, response in enumerate(responses)
    }
    choice_block = "\n".join(
        f"{index}. {response}" for index, response in numbered_options.items()
    )
    request = (
        f"{prompt}\n\n"
        "Choose exactly one option from the list below.\n"
        'Return JSON only in the form {"choice": <number>}.\n'
        f"Valid numbers: {', '.join(numbered_options.keys())}.\n\n"
        f"Options:\n{choice_block}"
    )

    last_raw = ""
    for attempts in range(_MAX_MULTIPLE_CHOICE_ATTEMPTS):
      temperature = 0.0 if attempts < 4 else 0.2
      options = _request_options(
          stop=(),
          temperature=temperature,
          top_p=0.9,
          top_k=40,
          max_tokens=64,
          seed=seed,
      )
      response = self._client.generate(
          model=self._model_name,
          prompt=f"{self._system_message}\n\n{request}",
          options=options,
          format="json",
          keep_alive=_DEFAULT_KEEP_ALIVE,
          think=False,
      )
      last_raw = response["response"].strip()
      parsed_choice = _extract_choice(last_raw, responses)
      if parsed_choice is None:
        continue

      if parsed_choice in numbered_options:
        idx = int(parsed_choice) - 1
        if self._measurements is not None:
          self._measurements.publish_datum(
              self._channel, {"choices_calls": attempts}
          )
        return idx, responses[idx], {"raw": last_raw}

      normalized = _normalize(parsed_choice)
      for idx, candidate in enumerate(responses):
        if normalized == _normalize(candidate):
          if self._measurements is not None:
            self._measurements.publish_datum(
                self._channel, {"choices_calls": attempts}
            )
          return idx, candidate, {"raw": last_raw}

    raise language_model.InvalidResponseError(
        f"Too many multiple choice attempts. Last attempt: {last_raw!r}"
    )


def _create_ollama_client() -> Any:
  try:
    ollama = importlib.import_module("ollama")
  except ImportError as error:
    raise ImportError(
        "Loveline debug Ollama runs require the optional ollama package. "
        "Install it with `pip install gdm-concordia[ollama]`."
    ) from error
  return ollama.Client()


def _request_options(
    *,
    stop: Collection[str],
    temperature: float,
    top_p: float | None = None,
    top_k: int | None = None,
    max_tokens: int | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
  options: dict[str, Any] = {
      "stop": list(stop),
      "temperature": temperature,
  }
  if top_p is not None:
    options["top_p"] = top_p
  if top_k is not None:
    options["top_k"] = top_k
  if max_tokens is not None and max_tokens > 0:
    options["num_predict"] = max_tokens
  if seed is not None:
    options["seed"] = seed
  return options


def _normalize(text: str) -> str:
  return re.sub(r"\s+", " ", text.strip().lower())


def _extract_continuation_prefix(prompt: str) -> str | None:
  if "Answer:" not in prompt:
    return None
  tail = prompt.rsplit("Answer:", 1)[1]
  prefix = tail.replace("\n", " ").strip()
  return prefix or None


def _build_generation_prompt(
    *,
    system_message: str,
    prompt: str,
    continuation_prefix: str | None,
) -> str:
  if not continuation_prefix or "Answer:" not in prompt:
    return f"{system_message}\n\n{prompt}"

  prompt_before_answer, _ = prompt.rsplit("Answer:", 1)
  return (
      f"{system_message}\n\n"
      "The prompt below ends with a partially written answer. The text after "
      "the final 'Answer:' has already started, and you must continue it "
      "without repeating any of the existing words. Return only the next "
      "words that should come after the existing answer text.\n\n"
      f"Existing answer text: {continuation_prefix!r}\n\n"
      f"{prompt_before_answer}Answer:"
  )


def _clean_sample_text(result: str, continuation_prefix: str | None) -> str:
  cleaned = _strip_repeated_prefix(result, continuation_prefix)
  cleaned = _strip_leading_answer_label(cleaned)
  cleaned = _strip_outer_quotes(cleaned)
  cleaned = _strip_quote_characters(cleaned)
  return cleaned.strip()


def _strip_repeated_prefix(result: str, continuation_prefix: str | None) -> str:
  cleaned = result.strip()
  if not continuation_prefix:
    return cleaned

  prefix = continuation_prefix.strip()
  normalized_prefix = _normalize(prefix)
  normalized_cleaned = _normalize(cleaned)
  if normalized_cleaned == normalized_prefix:
    return ""

  repeated_prefix = re.compile(
      rf"^{re.escape(prefix)}(?:[\s,:;.!?\-]+)?",
      re.IGNORECASE,
  )
  while repeated_prefix.match(cleaned):
    cleaned = repeated_prefix.sub("", cleaned, count=1).strip()
  cleaned = cleaned.lstrip(" ,:;.!?-")
  return cleaned.strip()


def _strip_leading_answer_label(text: str) -> str:
  return re.sub(
      r"^(?:answer|response)\s*:\s*", "", text.strip(), flags=re.IGNORECASE
  )


def _strip_outer_quotes(text: str) -> str:
  cleaned = text.strip()
  quote_pairs = (
      ('"', '"'),
      ("\u201c", "\u201d"),
      ("\u2018", "\u2019"),
      ("`", "`"),
  )

  changed = True
  while cleaned and changed:
    changed = False
    for opener, closer in quote_pairs:
      if cleaned.startswith(opener):
        cleaned = cleaned[len(opener) :].strip()
        if cleaned.endswith(closer):
          cleaned = cleaned[: -len(closer)].strip()
        changed = True
        break
      if cleaned.endswith(closer):
        cleaned = cleaned[: -len(closer)].strip()
        changed = True
        break
  return cleaned


def _strip_quote_characters(text: str) -> str:
  return text.translate(
      str.maketrans("", "", "\"\u201c\u201d`\u00ab\u00bb")
  ).strip()


def _contains_forbidden_stage_direction(text: str) -> bool:
  forbidden_patterns = (
      r"\bi take a breath\b",
      r"\bi let out a breath\b",
      r"\bi lower my voice\b",
      r"\bi raise my voice\b",
      r"\bi pause\b",
      r"\bi sigh\b",
      r"\bi laugh\b",
      r"\bi smile\b",
      r"\bi smirk\b",
      r"\bi shrug\b",
      r"\bi nod\b",
      r"\bi lean\b",
  )
  normalized = text.strip().lower()
  return any(re.search(pattern, normalized) for pattern in forbidden_patterns)


def _extract_choice(raw: str, responses: Sequence[str]) -> str | None:
  try:
    payload = json.loads(raw)
  except json.JSONDecodeError:
    payload = raw

  candidates: list[Any] = []
  if isinstance(payload, dict):
    candidates.extend((payload.get("choice"), payload.get("answer")))
    candidates.extend(payload.values())
  else:
    candidates.append(payload)

  valid_numbers = {str(index + 1) for index in range(len(responses))}
  for candidate in candidates:
    if candidate is None:
      continue
    text = str(candidate).strip()
    if text in valid_numbers:
      return text
    normalized = _normalize(text)
    for response in responses:
      if normalized == _normalize(response):
        return response
    match = re.search(r"\b(\d+)\b", text)
    if match and match.group(1) in valid_numbers:
      return match.group(1)
  return None
