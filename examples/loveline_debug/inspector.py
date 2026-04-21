"""Turn inspector over existing Loveline structured run artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from concordia.utils import structured_logging


_MAX_COMPONENTS = 12
_MAX_MEMORIES = 24
_MAX_GM_ENTRIES = 8
_MAX_TRANSCRIPT_TURNS = 3


def load_run_inspector(run_dir: Path) -> dict[str, Any]:
  """Builds browser-friendly inspector data for a completed/debug run."""
  log_path = run_dir / "structured_log.json"
  if not log_path.exists():
    return {
        "run_id": run_dir.name,
        "available": False,
        "error": "structured_log.json is not available for this run.",
        "overview": {},
        "entries": [],
        "selected": None,
  }

  log = structured_logging.SimulationLog.from_json(
      log_path.read_text(encoding="utf-8")
  )
  interface = structured_logging.AIAgentLogInterface(log)
  entries = _inspectable_entries(log, interface)
  selected = _selected_entry_payload(log, interface, entries[0]) if entries else None
  return {
      "run_id": run_dir.name,
      "available": True,
      "overview": interface.get_overview(),
      "entries": entries,
      "selected": selected,
  }


def load_turn_inspector(
    run_dir: Path,
    *,
    step: int,
    entity: str | None = None,
    index: int | None = None,
) -> dict[str, Any]:
  """Builds detail for one selected turn/entry from structured_log.json."""
  log_path = run_dir / "structured_log.json"
  log = structured_logging.SimulationLog.from_json(
      log_path.read_text(encoding="utf-8")
  )
  interface = structured_logging.AIAgentLogInterface(log)
  entries = _inspectable_entries(log, interface)
  selected = _match_entry(entries, step=step, entity=entity, index=index)
  if selected is None:
    raise ValueError(f"No inspectable entry found for step {step}.")
  return {
      "run_id": run_dir.name,
      "available": True,
      "overview": interface.get_overview(),
      "entries": entries,
      "selected": _selected_entry_payload(log, interface, selected),
  }


def load_first_turn_compare(left_run_dir: Path, right_run_dir: Path) -> dict[str, Any]:
  """Builds a side-by-side first-turn compare from existing run artifacts."""
  left = _compare_side(left_run_dir)
  right = _compare_side(right_run_dir)
  return {
      "available": left["available"] or right["available"],
      "left": left,
      "right": right,
      "diffs": _compare_diffs(left, right),
      "inputs": [
          "config_snapshot.json",
          "structured_log.json",
          "status.json transcript",
      ],
  }


def _inspectable_entries(
    log: structured_logging.SimulationLog,
    interface: structured_logging.AIAgentLogInterface,
) -> list[dict[str, Any]]:
  """Returns compact selectable entries, preferring agent turns."""
  action_entries = []
  for index, entry in enumerate(log.entries):
    if entry.entry_type != "entity":
      continue
    context = interface.get_entity_action_context(entry.entity_name, entry.step)
    if not context:
      continue
    action_entries.append({
        "index": index,
        "step": entry.step,
        "entity_name": entry.entity_name,
        "entry_type": entry.entry_type,
        "component_name": entry.component_name,
        "summary": entry.summary,
        "action": context.get("action", ""),
    })
  if action_entries:
    return action_entries

  return [
      {
          "index": index,
          "step": entry.step,
          "entity_name": entry.entity_name,
          "entry_type": entry.entry_type,
          "component_name": entry.component_name,
          "summary": entry.summary,
          "action": "",
      }
      for index, entry in enumerate(log.entries)
  ]


def _selected_entry_payload(
    log: structured_logging.SimulationLog,
    interface: structured_logging.AIAgentLogInterface,
    selected: dict[str, Any],
) -> dict[str, Any]:
  step = int(selected["step"])
  entity = selected["entity_name"]
  context = interface.get_entity_action_context(entity, step) or {}
  step_entries = interface.get_step_summary(step, include_content=True)
  gm_entries = _game_master_entries(step_entries, entity)
  action_prompt = context.get("action_prompt", "")
  observations = context.get("observations", [])
  components = _component_rows(context.get("all_components", {}))
  memories = interface.get_entity_memories(entity)[:_MAX_MEMORIES]
  gm_memories = interface.get_game_master_memories()[:_MAX_MEMORIES]

  raw_entry = log.entries[int(selected["index"])]
  return {
      "index": selected["index"],
      "step": step,
      "entity_name": entity,
      "entry_type": selected["entry_type"],
      "component_name": selected["component_name"],
      "summary": selected["summary"],
      "action": context.get("action") or selected.get("action", ""),
      "action_prompt": action_prompt,
      "observations": observations,
      "components": components,
      "entity_memories": memories,
      "game_master_memories": gm_memories,
      "game_master_entries": gm_entries,
      "raw_entry": {
          "step": raw_entry.step,
          "timestamp": raw_entry.timestamp,
          "entity_name": raw_entry.entity_name,
          "component_name": raw_entry.component_name,
          "entry_type": raw_entry.entry_type,
          "summary": raw_entry.summary,
          "data": log.reconstruct_value(raw_entry.deduplicated_data),
      },
  }


def _component_rows(components: Any) -> list[dict[str, Any]]:
  if not isinstance(components, dict):
    return []
  rows = []
  for name, value in components.items():
    if name in ("__act__", "__observation__"):
      continue
    rows.append({"name": name, "value": value})
  return rows[:_MAX_COMPONENTS]


def _game_master_entries(
    step_entries: list[dict[str, Any]],
    acting_entity: str,
) -> list[dict[str, Any]]:
  rows = []
  for entry in step_entries:
    if (
        entry.get("entry_type") == "entity"
        and entry.get("entity_name") == acting_entity
    ):
      continue
    rows.append({
        "step": entry.get("step"),
        "entity_name": entry.get("entity_name"),
        "component_name": entry.get("component_name"),
        "entry_type": entry.get("entry_type"),
        "summary": entry.get("summary"),
        "data": _extract_gm_context(entry.get("data")),
      })
  return rows[:_MAX_GM_ENTRIES]


def _extract_gm_context(data: Any) -> Any:
  if not isinstance(data, dict):
    return data
  value = data.get("value")
  if not isinstance(value, dict):
    return data
  compact: dict[str, Any] = {}
  for component_name, component_data in value.items():
    if not isinstance(component_data, dict):
      compact[component_name] = component_data
      continue
    component_context = {}
    for key in ("Value", "Summary", "Prompt", "Action Spec", "Key"):
      if key in component_data:
        component_context[key] = component_data[key]
    if component_context:
      compact[component_name] = component_context
  return compact or value


def _match_entry(
    entries: list[dict[str, Any]],
    *,
    step: int,
    entity: str | None,
    index: int | None,
) -> dict[str, Any] | None:
  for entry in entries:
    if index is not None and entry["index"] == index:
      return entry
  for entry in entries:
    if entry["step"] != step:
      continue
    if entity is not None and entry["entity_name"] != entity:
      continue
    return entry
  return None


def _compare_side(run_dir: Path) -> dict[str, Any]:
  config = _read_json_file(run_dir / "config_snapshot.json")
  status = _read_json_file(run_dir / "status.json")
  inspector_payload = load_run_inspector(run_dir)
  selected = inspector_payload.get("selected")
  return {
      "run_id": run_dir.name,
      "available": bool(inspector_payload.get("available") or config or status),
      "error": inspector_payload.get("error"),
      "config": _config_summary(config),
      "first_turn": _first_turn_summary(selected),
      "transcript": (status.get("transcript") or [])[:_MAX_TRANSCRIPT_TURNS],
      "artifacts": _artifact_summary(run_dir),
  }


def _read_json_file(path: Path) -> dict[str, Any]:
  if not path.exists():
    return {}
  try:
    payload = json.loads(path.read_text(encoding="utf-8"))
  except json.JSONDecodeError:
    return {}
  return payload if isinstance(payload, dict) else {}


def _config_summary(config: dict[str, Any]) -> dict[str, Any]:
  contestants = config.get("contestants") or []
  scene_defaults = config.get("scene_defaults") or {}
  run = config.get("run") or {}
  return {
      "snapshot_at": config.get("snapshot_at"),
      "candidates": [item.get("name") for item in contestants],
      "selected_candidate_ids": config.get("selected_candidate_ids") or [],
      "main_game_master": scene_defaults.get("main_game_master_name"),
      "scene_count": len(config.get("scenes") or []),
      "max_steps": run.get("max_steps"),
      "model": run.get("model_name"),
      "disable_language_model": run.get("disable_language_model"),
  }


def _first_turn_summary(turn: dict[str, Any] | None) -> dict[str, Any] | None:
  if not turn:
    return None
  return {
      "step": turn.get("step"),
      "entity_name": turn.get("entity_name"),
      "summary": turn.get("summary"),
      "action": turn.get("action"),
      "action_prompt": turn.get("action_prompt"),
      "observations": turn.get("observations") or [],
      "components": turn.get("components") or [],
      "game_master_entries": turn.get("game_master_entries") or [],
      "entity_memories": turn.get("entity_memories") or [],
      "game_master_memories": turn.get("game_master_memories") or [],
      "raw_entry": turn.get("raw_entry"),
  }


def _artifact_summary(run_dir: Path) -> dict[str, str]:
  artifacts = {}
  for name in ("config_snapshot", "structured_log", "status"):
    filename = f"{name}.json" if name != "structured_log" else "structured_log.json"
    path = run_dir / filename
    if path.exists():
      artifacts[name] = str(path)
  return artifacts


def _compare_diffs(
    left: dict[str, Any],
    right: dict[str, Any],
) -> list[dict[str, Any]]:
  diffs = []
  for label, path in (
      ("Candidates", ("config", "candidates")),
      ("Selected IDs", ("config", "selected_candidate_ids")),
      ("Scene Count", ("config", "scene_count")),
      ("Max Steps", ("config", "max_steps")),
      ("Model", ("config", "model")),
      ("First Actor", ("first_turn", "entity_name")),
      ("First Step", ("first_turn", "step")),
      ("First Action", ("first_turn", "action")),
  ):
    left_value = _nested_get(left, path)
    right_value = _nested_get(right, path)
    if left_value != right_value:
      diffs.append({"label": label, "left": left_value, "right": right_value})
  return diffs


def _nested_get(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
  value: Any = payload
  for key in path:
    if not isinstance(value, dict):
      return None
    value = value.get(key)
  return value


def json_safe(payload: Any) -> Any:
  """Returns a JSON-safe copy for tests and defensive endpoint output."""
  return json.loads(json.dumps(payload, ensure_ascii=False, default=str))
