"""Draft snapshots and Concordia config construction for Loveline debug UI."""

from __future__ import annotations

import copy
import dataclasses
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import yaml

from concordia.prefabs import entity as entity_prefabs
from concordia.prefabs import game_master as game_master_prefabs
from concordia.prefabs.game_master import formative_memories_initializer
from concordia.typing import entity as entity_lib
from concordia.typing import prefab as prefab_lib
from concordia.typing import scene as scene_lib
from examples.loveline_debug import basic_entity_controls
from examples.loveline_debug import dialogic_and_dramaturgic as loveline_dialogic_and_dramaturgic
from examples.loveline_debug import scene_type_instructions


STARTER_ROOT = Path(
    "/Users/claw/.openclaw/games/loveline/concordia_dating_show_starter"
)
DRAFT_SCHEMA_VERSION = 1
DEFAULT_API_TYPE = "ollama"
DEFAULT_MODEL_NAME = "qwen3.5:35b-a3b"
DEFAULT_SKIP_GENERATED_FORMATIVE_MEMORIES = False
DEFAULT_STRICT_CANDIDATE_FACT_ANCHORING = False
BASIC_ENTITY_HISTORY_LENGTH_DEFAULTS = {
    "observation_history_length": 1_000_000,
    "situation_perception_history_length": 25,
    "self_perception_history_length": 1_000_000,
    "person_by_situation_history_length": 5,
}
STOCK_BASIC_ENTITY_COMPONENT_DEFAULTS = (
    basic_entity_controls.STOCK_BASIC_ENTITY_COMPONENT_DEFAULTS
)


class DraftValidationError(ValueError):
  """Raised when a Loveline draft cannot be run."""


@dataclasses.dataclass(frozen=True)
class StarterPaths:
  root: Path = STARTER_ROOT

  @property
  def personas_yaml(self) -> Path:
    return self.root / "personas" / "personas.yaml"

  @property
  def scenes_yaml(self) -> Path:
    return self.root / "scenes" / "scenes.yaml"

  @property
  def persona_bundle_json(self) -> Path:
    return self.root / "generated" / "persona_bundle.json"

  @property
  def debug_root(self) -> Path:
    return self.root / "generated" / "loveline_debug"

  @property
  def drafts_dir(self) -> Path:
    return self.debug_root / "drafts"

  @property
  def contestants_json(self) -> Path:
    return self.debug_root / "contestants.json"

  @property
  def runs_dir(self) -> Path:
    return self.debug_root / "runs"


def load_json(path: Path) -> dict[str, Any]:
  return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(
      json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
      encoding="utf-8",
  )


def load_yaml(path: Path) -> dict[str, Any]:
  with path.open("r", encoding="utf-8") as handle:
    return yaml.safe_load(handle)


def _candidate_gender(candidate: dict[str, Any]) -> str:
  tags = candidate.get("derived_debug_tags", [])
  if tags and tags[0] in ("man", "woman"):
    return tags[0]
  name = candidate.get("name")
  return str(candidate.get("gender") or name or "")


def _safe_id(value: str) -> str:
  safe = _safe_name(value.strip().lower().replace(" ", "_"))
  return safe or "contestant"


def _apply_candidate_defaults(candidate: dict[str, Any]) -> dict[str, Any]:
  candidate = copy.deepcopy(candidate)
  entity_params = candidate.setdefault("entity_params", {})
  if candidate.get("name"):
    entity_params.setdefault("name", candidate["name"])
  for key, value in BASIC_ENTITY_HISTORY_LENGTH_DEFAULTS.items():
    entity_params.setdefault(key, value)
  component_cfg = entity_params.setdefault("stock_basic_entity_components", {})
  if not isinstance(component_cfg, dict):
    component_cfg = {}
    entity_params["stock_basic_entity_components"] = component_cfg
  for key, value in STOCK_BASIC_ENTITY_COMPONENT_DEFAULTS.items():
    component_cfg.setdefault(key, value)
  candidate["gender"] = candidate.get("gender") or _candidate_gender(candidate)
  return candidate


def _source_candidates(paths: StarterPaths) -> list[dict[str, Any]]:
  personas = load_yaml(paths.personas_yaml)
  bundle = load_json(paths.persona_bundle_json)
  by_id = {item["id"]: item for item in bundle["contestants"]}
  result = []
  for persona in personas.get("contestants", []):
    candidate = copy.deepcopy(by_id[persona["id"]])
    candidate["source_persona"] = persona
    candidate["gender"] = persona.get("gender", _candidate_gender(candidate))
    candidate["age"] = persona.get("age")
    result.append(_apply_candidate_defaults(candidate))
  return result


def _saved_candidate_overrides(paths: StarterPaths) -> dict[str, dict[str, Any]]:
  if not paths.contestants_json.exists():
    return {}
  payload = load_json(paths.contestants_json)
  if isinstance(payload, list):
    return {
        item["id"]: item
        for item in payload
        if isinstance(item, dict) and item.get("id")
    }
  return {
      candidate_id: item
      for candidate_id, item in payload.items()
      if isinstance(item, dict)
  }


def list_candidates(paths: StarterPaths = StarterPaths()) -> list[dict[str, Any]]:
  """Returns the shared canonical contestant list used by every draft."""
  try:
    source_candidates = _source_candidates(paths)
  except FileNotFoundError:
    source_candidates = []
  by_id = {item["id"]: item for item in source_candidates}
  for candidate_id, saved in _saved_candidate_overrides(paths).items():
    base = by_id.get(candidate_id, {})
    merged = {**copy.deepcopy(base), **copy.deepcopy(saved), "id": candidate_id}
    if base.get("entity_params") or saved.get("entity_params"):
      merged["entity_params"] = {
          **copy.deepcopy(base.get("entity_params") or {}),
          **copy.deepcopy(saved.get("entity_params") or {}),
      }
    by_id[candidate_id] = _apply_candidate_defaults(merged)
  return list(by_id.values())


def save_contestant(
    contestant: dict[str, Any],
    paths: StarterPaths = StarterPaths(),
) -> dict[str, Any]:
  """Creates or updates one shared contestant record."""
  candidate = _apply_candidate_defaults(contestant)
  candidate_id = candidate.get("id") or _safe_id(candidate.get("name", "contestant"))
  existing_ids = {item["id"] for item in list_candidates(paths)}
  if candidate_id in existing_ids and candidate.get("id") != candidate_id:
    suffix = 2
    base_id = candidate_id
    while candidate_id in existing_ids:
      candidate_id = f"{base_id}_{suffix}"
      suffix += 1
  candidate["id"] = candidate_id
  overrides = _saved_candidate_overrides(paths)
  overrides[candidate_id] = candidate
  write_json(paths.contestants_json, overrides)
  return candidate


def create_contestant(
    contestant: dict[str, Any],
    paths: StarterPaths = StarterPaths(),
) -> dict[str, Any]:
  candidate = copy.deepcopy(contestant)
  candidate.pop("id", None)
  name = candidate.get("name") or "New Contestant"
  base_id = _safe_id(name)
  existing_ids = {item["id"] for item in list_candidates(paths)}
  candidate_id = base_id
  suffix = 2
  while candidate_id in existing_ids:
    candidate_id = f"{base_id}_{suffix}"
    suffix += 1
  candidate["id"] = candidate_id
  return save_contestant(candidate, paths)


def list_source_data(paths: StarterPaths = StarterPaths()) -> dict[str, Any]:
  scenes = load_yaml(paths.scenes_yaml)
  return {
      "starter_root": str(paths.root),
      "candidates": list_candidates(paths),
      "scene_defaults": scenes.get("defaults", {}),
      "scene_types": scenes.get("scene_types", {}),
      "scenes": scenes.get("scenes", []),
  }


def _scene_mentions(scene: dict[str, Any], selected_names: set[str]) -> bool:
  participants = set(scene.get("participants", []))
  return bool(participants) and participants.issubset(selected_names)


def make_default_draft(paths: StarterPaths = StarterPaths()) -> dict[str, Any]:
  source = list_source_data(paths)
  candidates = source["candidates"]
  man = next(item for item in candidates if item["gender"] == "man")
  woman = next(item for item in candidates if item["gender"] == "woman")
  return make_draft_for_selection([man["id"], woman["id"]], paths)


def make_draft_for_selection(
    candidate_ids: list[str],
    paths: StarterPaths = StarterPaths(),
) -> dict[str, Any]:
  source = list_source_data(paths)
  by_id = {item["id"]: item for item in source["candidates"]}
  contestants = [copy.deepcopy(by_id[candidate_id]) for candidate_id in candidate_ids]
  selected_names = {item["name"] for item in contestants}
  scenes = [
      copy.deepcopy(scene)
      for scene in source["scenes"]
      if _scene_mentions(scene, selected_names)
  ]
  now = dt.datetime.now(dt.timezone.utc).isoformat()
  return {
      "schema_version": DRAFT_SCHEMA_VERSION,
      "name": "two_candidate_debug",
      "created_at": now,
      "updated_at": now,
      "source_root": str(paths.root),
      "selected_candidate_ids": candidate_ids,
      "contestants": contestants,
      "scene_defaults": copy.deepcopy(source["scene_defaults"]),
      "scene_types": copy.deepcopy(source["scene_types"]),
      "scenes": scenes,
      "run": {
          "max_steps": 8,
          "disable_language_model": False,
          "api_type": DEFAULT_API_TYPE,
          "model_name": DEFAULT_MODEL_NAME,
          "api_key": None,
          "start_paused": True,
          "checkpoint_every_step": True,
          "skip_generated_formative_memories": (
              DEFAULT_SKIP_GENERATED_FORMATIVE_MEMORIES
          ),
          "strict_candidate_fact_anchoring": (
              DEFAULT_STRICT_CANDIDATE_FACT_ANCHORING
          ),
      },
  }


def hydrate_draft(
    draft: dict[str, Any],
    paths: StarterPaths | None = None,
) -> dict[str, Any]:
  """Attaches canonical contestants to a draft that stores selected ids."""
  draft = copy.deepcopy(draft)
  selected_ids = list(draft.get("selected_candidate_ids") or [])
  if not selected_ids and draft.get("contestants"):
    selected_ids = [item.get("id") for item in draft["contestants"] if item.get("id")]
    draft["selected_candidate_ids"] = selected_ids
  source_root = Path(draft.get("source_root", paths.root if paths else STARTER_ROOT))
  candidate_paths = paths or StarterPaths(source_root)
  by_id = {item["id"]: item for item in list_candidates(candidate_paths)}
  legacy_by_id = {
      item.get("id"): item
      for item in draft.get("contestants", [])
      if isinstance(item, dict) and item.get("id")
  }
  draft["contestants"] = [
      copy.deepcopy(legacy_by_id.get(candidate_id) or by_id[candidate_id])
      for candidate_id in selected_ids
      if candidate_id in by_id or candidate_id in legacy_by_id
  ]
  return draft


def normalized_draft_for_storage(draft: dict[str, Any]) -> dict[str, Any]:
  stored = copy.deepcopy(draft)
  stored.pop("contestants", None)
  return stored


def validate_draft(draft: dict[str, Any]) -> None:
  draft = hydrate_draft(draft)
  contestants = draft.get("contestants", [])
  if len(contestants) != 2:
    raise DraftValidationError("Draft must contain exactly 2 candidates.")
  genders = sorted(_candidate_gender(item) for item in contestants)
  if genders != ["man", "woman"]:
    raise DraftValidationError("Draft must contain exactly 1 man and 1 woman.")
  names = {item.get("name") for item in contestants}
  if len(names) != 2 or None in names:
    raise DraftValidationError("Draft candidates must have unique names.")
  for scene in draft.get("scenes", []):
    participants = set(scene.get("participants", []))
    if not participants.issubset(names):
      raise DraftValidationError(
          f"Scene {scene.get('id', '<unnamed>')} contains non-selected players."
      )


def save_draft(
    draft: dict[str, Any],
    name: str | None = None,
    paths: StarterPaths = StarterPaths(),
) -> Path:
  for contestant in draft.get("contestants") or []:
    save_contestant(contestant, paths)
  draft = hydrate_draft(draft, paths)
  validate_draft(draft)
  clean_name = _safe_name(name or draft.get("name") or "draft")
  draft = normalized_draft_for_storage(draft)
  draft["name"] = clean_name
  draft["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
  path = paths.drafts_dir / f"{clean_name}.json"
  write_json(path, draft)
  return path


def list_drafts(paths: StarterPaths = StarterPaths()) -> list[dict[str, Any]]:
  if not paths.drafts_dir.exists():
    return []
  drafts = []
  for path in sorted(paths.drafts_dir.glob("*.json")):
    try:
      payload = load_json(path)
    except json.JSONDecodeError:
      continue
    drafts.append({
        "name": path.stem,
        "path": str(path),
        "updated_at": payload.get("updated_at"),
        "candidates": [
            item.get("name")
            for item in hydrate_draft(payload, paths).get("contestants", [])
        ],
      })
  return drafts


def load_draft(name: str, paths: StarterPaths = StarterPaths()) -> dict[str, Any]:
  return hydrate_draft(load_json(paths.drafts_dir / f"{_safe_name(name)}.json"), paths)


def _safe_name(name: str) -> str:
  return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name)


def deterministic_embedder(text: str):
  del text
  try:
    import numpy as np  # pylint: disable=import-outside-toplevel

    return np.zeros(16, dtype=np.float32)
  except ImportError:
    return [0.0] * 16


def build_scene_specs(draft: dict[str, Any], gm_name: str) -> list[scene_lib.SceneSpec]:
  scene_types_cfg = draft["scene_types"]
  scene_type_specs: dict[str, scene_lib.SceneTypeSpec] = {}
  for scene_type_name, cfg in scene_types_cfg.items():
    scene_type_specs[scene_type_name] = scene_lib.SceneTypeSpec(
        name=scene_type_name,
        game_master_name=gm_name,
        action_spec=entity_lib.free_action_spec(
            call_to_action=cfg["call_to_action"]
        ),
    )

  specs = []
  for item in draft["scenes"]:
    scene_type_name = item["type"]
    specs.append(
        scene_lib.SceneSpec(
            scene_type=scene_type_specs[scene_type_name],
            participants=item["participants"],
            num_rounds=item.get(
                "num_rounds", scene_types_cfg[scene_type_name]["rounds"]
            ),
            premise=item.get("premise"),
        )
    )
  return specs


def build_config(draft: dict[str, Any]) -> prefab_lib.Config:
  draft = hydrate_draft(draft)
  validate_draft(draft)
  contestants = draft["contestants"]
  player_names = [item["name"] for item in contestants]
  run_settings = draft.get("run") or {}
  gm_name = draft["scene_defaults"].get("main_game_master_name", "Show Runner")
  scene_type_overrides = scene_type_instructions.scene_type_instruction_overrides(
      draft["scene_types"]
  )
  scene_type_examples = scene_type_instructions.scene_type_examples_overrides(
      draft["scene_types"]
  )
  scene_type_context = scene_type_instructions.scene_type_context_overrides(
      draft["scene_types"]
  )
  scene_type_memory_overrides = (
      scene_type_instructions.scene_type_memory_overrides(
          draft["scene_types"]
      )
  )
  scene_type_memory_filters = scene_type_instructions.scene_type_memory_filters(
      draft["scene_types"]
  )
  source_root = Path(draft.get("source_root", STARTER_ROOT))
  shared_memories = (
      load_json(StarterPaths(source_root).persona_bundle_json)
      .get("show", {})
      .get("shared_memories", [])
  )

  instances: list[prefab_lib.InstanceConfig] = []
  for contestant in contestants:
    instances.append(
        prefab_lib.InstanceConfig(
            prefab=contestant.get("prefab", "basic__Entity"),
            role=prefab_lib.Role.ENTITY,
            params=copy.deepcopy(contestant["entity_params"]),
        )
    )

  anchored_contexts = {
      item["name"]: _anchored_player_specific_context(
          item,
          enabled=run_settings.get("strict_candidate_fact_anchoring", False),
      )
      for item in contestants
  }
  anchored_memories = {
      item["name"]: _anchored_player_specific_memories(
          item,
          enabled=run_settings.get("strict_candidate_fact_anchoring", False),
      )
      for item in contestants
  }
  instances.append(
      prefab_lib.InstanceConfig(
          prefab="formative_memories_initializer__GameMaster",
          role=prefab_lib.Role.INITIALIZER,
          params={
              "name": "Backstory Initializer",
              "next_game_master_name": gm_name,
              "shared_memories": shared_memories,
              "player_specific_context": anchored_contexts,
              "player_specific_memories": anchored_memories,
              "skip_formative_memories_for": (
                  player_names
                  if run_settings.get("skip_generated_formative_memories", False)
                  else []
              ),
          },
      )
  )
  instances.append(
      prefab_lib.InstanceConfig(
          prefab="loveline_dialogic_and_dramaturgic__GameMaster",
          role=prefab_lib.Role.GAME_MASTER,
          params={
              "name": gm_name,
              "scenes": build_scene_specs(draft, gm_name),
              "allow_llm_fallback": False,
              **_scene_type_gm_prompt_overrides(
                  scene_type_overrides=scene_type_overrides,
                  scene_type_examples=scene_type_examples,
                  scene_type_context=scene_type_context,
                  scene_type_memory_overrides=scene_type_memory_overrides,
                  scene_type_memory_filters=scene_type_memory_filters,
              ),
          },
      )
  )
  return prefab_lib.Config(
      prefabs={
          "basic__Entity": basic_entity_controls.Entity(),
          "basic_with_plan__Entity": entity_prefabs.basic_with_plan.Entity(),
          "conversational__Entity": entity_prefabs.conversational.Entity(),
          "dialogic_and_dramaturgic__GameMaster": (
              game_master_prefabs.dialogic_and_dramaturgic.GameMaster()
          ),
          "loveline_dialogic_and_dramaturgic__GameMaster": (
              loveline_dialogic_and_dramaturgic.GameMaster()
          ),
          "formative_memories_initializer__GameMaster": (
              formative_memories_initializer.GameMaster()
          ),
      },
      instances=instances,
      default_premise=draft["scene_defaults"]["default_premise"],
      default_max_steps=int(run_settings.get("max_steps") or 8),
  )


def snapshot_for_run(draft: dict[str, Any], run_id: str) -> dict[str, Any]:
  snapshot = hydrate_draft(draft)
  snapshot["run_id"] = run_id
  snapshot["snapshot_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
  validate_draft(snapshot)
  return snapshot


def _scene_type_gm_prompt_overrides(
    *,
    scene_type_overrides: dict[str, str],
    scene_type_examples: dict[str, str],
    scene_type_context: dict[str, str],
    scene_type_memory_overrides: dict[str, str],
    scene_type_memory_filters: dict[str, str],
) -> dict[str, Any]:
  replacement_components = {}
  extra_components = {}
  extra_components_index = {}
  if scene_type_overrides:
    replacement_components["instructions"] = (
        scene_type_instructions.SceneTypeInstructionsOverride(
            scene_type_overrides
        )
    )
  if scene_type_examples:
    replacement_components["examples"] = (
        scene_type_instructions.SceneTypeExamplesOverride(scene_type_examples)
    )
  if scene_type_context:
    extra_components["scene_type_context"] = (
        scene_type_instructions.SceneTypeContextOverride(scene_type_context)
    )
    extra_components_index["scene_type_context"] = 3
  if scene_type_memory_overrides or scene_type_memory_filters:
    extra_components["scene_type_memory"] = (
        scene_type_instructions.SceneTypeMemoryOverrideOrFilter(
            scene_type_memory_overrides,
            scene_type_memory_filters,
        )
    )
    extra_components_index["scene_type_memory"] = 4
  if not replacement_components and not extra_components:
    return {}
  payload = {}
  if replacement_components:
    payload["replacement_components"] = replacement_components
  if extra_components:
    payload["extra_components"] = extra_components
  if extra_components_index:
    payload["extra_components_index"] = extra_components_index
  return payload


def _anchored_player_specific_context(
    contestant: dict[str, Any],
    *,
    enabled: bool,
) -> str:
  context = str(contestant.get("player_specific_context", "") or "")
  if not enabled:
    return context
  facts = _contestant_fact_anchor_lines(contestant)
  if not facts:
    return context
  prefix = "\n".join([
      "Strict factual anchor instructions:",
      (
          "Do not contradict known basic biographical facts for this contestant."
      ),
      (
          "Keep age, job, pets, siblings, and other fixed personal details"
          " consistent. If a detail is unknown, avoid inventing a conflicting"
          " one."
      ),
      *facts,
  ])
  if not context.strip():
    return prefix
  return f"{prefix}\n\n{context}"


def _anchored_player_specific_memories(
    contestant: dict[str, Any],
    *,
    enabled: bool,
) -> list[str]:
  memories = list(contestant.get("player_specific_memories", []) or [])
  if not enabled:
    return memories
  facts = _contestant_fact_anchor_lines(contestant)
  if not facts:
    return memories
  return [
      (
          "Fixed factual anchors: Do not contradict these known basics. "
          + " ".join(facts)
      ),
      *memories,
  ]


def _contestant_fact_anchor_lines(contestant: dict[str, Any]) -> list[str]:
  lines = []
  name = str(contestant.get("name") or "").strip()
  if name:
    lines.append(f"Name: {name}.")
  age = contestant.get("age")
  if age not in (None, ""):
    lines.append(f"Age: {age}.")

  source_persona = contestant.get("source_persona") or {}
  occupation = (
      source_persona.get("core_identity", {}).get("occupation")
      or _context_line_value(contestant.get("player_specific_context", ""), "Occupation")
  )
  if occupation:
    lines.append(f"Occupation: {occupation}.")

  hometown = source_persona.get("core_identity", {}).get("hometown")
  if hometown:
    lines.append(f"Hometown: {hometown}.")

  lines.extend(
      _memory_fact_lines(
          contestant.get("player_specific_memories", []) or []
      )
  )
  deduped = []
  for line in lines:
    clean = str(line).strip()
    if clean and clean not in deduped:
      deduped.append(clean)
  return deduped


def _context_line_value(context: str, label: str) -> str:
  prefix = f"{label}:"
  for line in str(context or "").splitlines():
    if line.startswith(prefix):
      return line.removeprefix(prefix).strip()
  return ""


def _memory_fact_lines(memories: list[str]) -> list[str]:
  facts = []
  for memory in memories:
    text = str(memory).strip()
    lowered = text.lower()
    if not text:
      continue
    if "sibling" in lowered and text not in facts:
      facts.append(text if text.endswith(".") else f"{text}.")
      continue
    if re.search(r"\b(dog|cat|pets?)\b", lowered) and text not in facts:
      facts.append(text if text.endswith(".") else f"{text}.")
  return facts[:4]
