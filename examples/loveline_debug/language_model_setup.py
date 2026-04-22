"""Language-model setup local to the Loveline debug UI."""

from __future__ import annotations

from concordia.contrib import language_models
from concordia.language_model import language_model
from concordia.language_model import no_language_model

from examples.loveline_debug import ollama_shim


def setup(
    *,
    api_type: str,
    model_name: str,
    api_key: str | None = None,
    disable_language_model: bool = False,
) -> language_model.LanguageModel:
  """Builds a model for Loveline debug runs."""
  if disable_language_model:
    return no_language_model.NoLanguageModel()
  if api_type == "ollama":
    if api_key:
      raise ValueError("Loveline debug Ollama runs do not use api_key.")
    return ollama_shim.LovelineOllamaLanguageModel(model_name=model_name)
  return language_models.language_model_setup(
      api_type=api_type,
      model_name=model_name,
      api_key=api_key,
      disable_language_model=False,
  )
