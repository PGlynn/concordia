"""Loveline-local spoken-output verification and retry wrapper."""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
import dataclasses
import re
import threading
from typing import Any

from concordia.language_model import language_model


_DEFAULT_BANNED_TERMS = (
    "quiet",
    "comfort",
    "real",
    "safe",
    "romantic",
    "feel",
    "perform",
)
_SPOKEN_DIALOGUE_MARKER = (
    "For free-action dialogue, respond only with the exact spoken words "
    "the character says in first person."
)
_INTERNAL_QUESTION_PREFIXES = (
    "what situation is ",
    "what kind of person is ",
    "what would a person like ",
)


@dataclasses.dataclass(frozen=True)
class SpokenOutputGuardConfig:
  """Opt-in Loveline-local controls for spoken actor outputs."""

  enabled: bool = False
  banned_terms: tuple[str, ...] = _DEFAULT_BANNED_TERMS
  max_retries: int = 2
  reject_speaker_labels: bool = True
  reject_narration: bool = True
  topic_schedule: tuple[str, ...] = ()
  fail_on_exhausted_retries: bool = True

  @classmethod
  def from_payload(
      cls, payload: Mapping[str, Any] | None
  ) -> "SpokenOutputGuardConfig":
    payload = payload or {}
    banned_terms = payload.get("banned_terms", _DEFAULT_BANNED_TERMS)
    topic_schedule = payload.get("topic_schedule", ())
    return cls(
        enabled=bool(payload.get("enabled", False)),
        banned_terms=tuple(
            str(item).strip()
            for item in banned_terms
            if str(item).strip()
        ),
        max_retries=max(0, int(payload.get("max_retries", 2))),
        reject_speaker_labels=bool(
            payload.get("reject_speaker_labels", True)
        ),
        reject_narration=bool(payload.get("reject_narration", True)),
        topic_schedule=tuple(
            str(item).strip()
            for item in topic_schedule
            if str(item).strip()
        ),
        fail_on_exhausted_retries=bool(
            payload.get("fail_on_exhausted_retries", True)
        ),
    )

  def to_payload(self) -> dict[str, Any]:
    return {
        "enabled": self.enabled,
        "banned_terms": list(self.banned_terms),
        "max_retries": self.max_retries,
        "reject_speaker_labels": self.reject_speaker_labels,
        "reject_narration": self.reject_narration,
        "topic_schedule": list(self.topic_schedule),
        "fail_on_exhausted_retries": self.fail_on_exhausted_retries,
    }


class SpokenOutputGuard(language_model.LanguageModel):
  """Wraps a model with Loveline-local spoken output verification."""

  def __init__(
      self,
      model: language_model.LanguageModel,
      config: SpokenOutputGuardConfig,
  ) -> None:
    self._model = model
    self._config = config
    self._lock = threading.Lock()
    self._spoken_turn_index = 0

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
    if not self._config.enabled or not is_spoken_actor_prompt(prompt):
      return self._model.sample_text(
          prompt,
          max_tokens=max_tokens,
          terminators=terminators,
          temperature=temperature,
          top_p=top_p,
          top_k=top_k,
          timeout=timeout,
          seed=seed,
      )

    with self._lock:
      turn_index = self._spoken_turn_index
      self._spoken_turn_index += 1
    topic = scheduled_topic(self._config, turn_index)

    last_result = ""
    last_violations: tuple[str, ...] = ()
    for attempt in range(self._config.max_retries + 1):
      guarded_prompt = _guarded_prompt(
          prompt,
          config=self._config,
          topic=topic,
          previous_output=last_result if attempt else None,
          violations=last_violations,
      )
      attempt_seed = None if seed is None else seed + attempt
      result = self._model.sample_text(
          guarded_prompt,
          max_tokens=max_tokens,
          terminators=terminators,
          temperature=temperature,
          top_p=top_p,
          top_k=top_k,
          timeout=timeout,
          seed=attempt_seed,
      )
      violations = verify_spoken_output(result, self._config)
      if not violations:
        return result
      last_result = result
      last_violations = tuple(violations)

    if self._config.fail_on_exhausted_retries:
      raise language_model.InvalidResponseError(
          "Loveline spoken output verifier rejected the final attempt: "
          + "; ".join(last_violations)
          + f". Last output: {last_result!r}"
      )
    return last_result

  def sample_choice(
      self,
      prompt: str,
      responses: Sequence[str],
      *,
      seed: int | None = None,
  ) -> tuple[int, str, Mapping[str, Any]]:
    return self._model.sample_choice(prompt, responses, seed=seed)


def is_spoken_actor_prompt(prompt: str) -> bool:
  """Returns True for the final free-action spoken turn prompt only."""
  if _SPOKEN_DIALOGUE_MARKER not in prompt:
    return False
  question = _last_question(prompt)
  if not question:
    return False
  normalized = re.sub(r"\s+", " ", question.strip().lower())
  return not normalized.startswith(_INTERNAL_QUESTION_PREFIXES)


def scheduled_topic(
    config: SpokenOutputGuardConfig, turn_index: int
) -> str | None:
  if turn_index < 0 or turn_index >= len(config.topic_schedule):
    return None
  return config.topic_schedule[turn_index]


def verify_spoken_output(
    text: str, config: SpokenOutputGuardConfig
) -> list[str]:
  """Returns violations for a candidate spoken line."""
  violations = []
  stripped = text.strip()
  if not stripped:
    return ["empty output"]
  banned_terms = _matched_banned_terms(stripped, config.banned_terms)
  if banned_terms:
    violations.append("banned terms: " + ", ".join(banned_terms))
  if config.reject_speaker_labels and _has_speaker_label(stripped):
    violations.append("speaker labels are not allowed")
  if config.reject_narration and _has_narration(stripped):
    violations.append("narration or stage directions are not allowed")
  return violations


def _guarded_prompt(
    prompt: str,
    *,
    config: SpokenOutputGuardConfig,
    topic: str | None,
    previous_output: str | None,
    violations: Sequence[str],
) -> str:
  lines = [
      "Loveline local debug spoken-output verifier is enabled for this run.",
      "Return one line of spoken dialogue only.",
  ]
  if config.reject_speaker_labels:
    lines.append("Do not prefix the line with the speaker name or any label.")
  if config.reject_narration:
    lines.append(
        "Do not include narration, stage directions, gestures, or bracketed text."
    )
  if config.banned_terms:
    lines.append(
        "Avoid these banned terms: " + ", ".join(config.banned_terms) + "."
    )
  if topic:
    lines.append("Turn topic focus: " + topic + ".")
  if previous_output is not None:
    lines.append("Previous invalid attempt: " + repr(previous_output) + ".")
  if violations:
    lines.append("Fix these issues: " + "; ".join(violations) + ".")
  return "\n".join(lines) + "\n\n" + prompt


def _matched_banned_terms(
    text: str, banned_terms: Sequence[str]
) -> list[str]:
  matched = []
  for term in banned_terms:
    if re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE):
      matched.append(term)
  return matched


def _has_speaker_label(text: str) -> bool:
  return bool(
      re.match(
          r"^\s*[A-Z][\w'’-]*(?:\s+[A-Z][\w'’-]*){0,2}\s*:\s+",
          text,
      )
  )


def _has_narration(text: str) -> bool:
  return bool(
      re.search(r"[\(\[\*].*?[\)\]\*]", text)
      or re.search(r"^\s*(?:Narration|Action)\s*:", text, flags=re.IGNORECASE)
  )


def _last_question(prompt: str) -> str | None:
  matches = re.findall(r"Question:\s*(.+?)(?:\nAnswer:|\Z)", prompt, re.DOTALL)
  if not matches:
    return None
  return matches[-1].strip()
