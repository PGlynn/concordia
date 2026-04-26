"""Language-model setup local to the Loveline debug UI."""

from __future__ import annotations

from concordia.contrib import language_models
from concordia.language_model import language_model
from concordia.language_model import no_language_model

from examples.loveline_debug import codex_oauth_shim
from examples.loveline_debug import ollama_shim
from examples.loveline_debug import output_guard


def setup(
    *,
    api_type: str,
    model_name: str,
    api_key: str | None = None,
    disable_language_model: bool = False,
    spoken_output_verifier: dict[str, object] | None = None,
) -> language_model.LanguageModel:
  """Builds a model for Loveline debug runs."""
  if disable_language_model:
    return no_language_model.NoLanguageModel()
  model: language_model.LanguageModel
  if api_type == "ollama":
    if api_key:
      raise ValueError("Loveline debug Ollama runs do not use api_key.")
    model = ollama_shim.LovelineOllamaLanguageModel(model_name=model_name)
  elif api_type == "codex_oauth":
    if api_key:
      raise ValueError(
          "Loveline debug Codex OAuth runs use the server-side Codex CLI "
          "login session, not api_key."
      )
    model = codex_oauth_shim.LovelineCodexOAuthLanguageModel(
        model_name=model_name
    )
  else:
    model = language_models.language_model_setup(
        api_type=api_type,
        model_name=model_name,
        api_key=api_key,
        disable_language_model=False,
    )
  verifier_config = output_guard.SpokenOutputGuardConfig.from_payload(
      spoken_output_verifier
  )
  if verifier_config.enabled:
    return output_guard.SpokenOutputGuard(model, verifier_config)
  return model
