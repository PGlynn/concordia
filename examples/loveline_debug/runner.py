"""Run Loveline drafts through stock Concordia surfaces."""

from __future__ import annotations

import collections.abc
import dataclasses
import datetime as dt
import json
import shutil
import threading
import traceback
from pathlib import Path
from typing import Any

from concordia.language_model import no_language_model
from concordia.prefabs.simulation import generic as simulation
from concordia.utils import simulation_server
from concordia.utils import visual_interface

from examples.loveline_debug import config_io
from examples.loveline_debug import language_model_setup


@dataclasses.dataclass
class RunRecord:
  run_id: str
  status: str
  run_dir: Path
  started_at: str
  finished_at: str | None = None
  error: str | None = None
  current_step: int = 0
  start_paused: bool = True
  summary: dict[str, Any] = dataclasses.field(default_factory=dict)
  transcript: list[dict[str, Any]] = dataclasses.field(default_factory=list)
  artifacts: dict[str, str] = dataclasses.field(default_factory=dict)

  def to_dict(self) -> dict[str, Any]:
    return {
        "run_id": self.run_id,
        "status": self.status,
        "run_dir": str(self.run_dir),
        "started_at": self.started_at,
        "finished_at": self.finished_at,
        "error": self.error,
        "current_step": self.current_step,
        "start_paused": self.start_paused,
        "summary": _json_safe(self.summary),
        "transcript": _json_safe(self.transcript[-80:]),
        "artifacts": _json_safe(self.artifacts),
    }


class RunManager:
  """Owns one active Loveline debug run and recent run metadata."""

  def __init__(self, paths: config_io.StarterPaths = config_io.StarterPaths()):
    self._paths = paths
    self._lock = threading.Lock()
    self._active: RunRecord | None = None
    self._active_control: simulation_server.SimulationServer | None = None

  def start_run(self, draft: dict[str, Any]) -> RunRecord:
    with self._lock:
      if self._active and self._active.status in ("starting", "running"):
        raise RuntimeError(f"Run {self._active.run_id} is already active.")
      run_id = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
      run_dir = self._paths.runs_dir / run_id
      start_paused = draft.get("run", {}).get("start_paused", True) is not False
      control = simulation_server.SimulationServer(html_content="")
      if not start_paused:
        control.step_controller.play()
      record = RunRecord(
          run_id=run_id,
          status="starting",
          run_dir=run_dir,
          started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
          start_paused=start_paused,
          summary=_draft_summary(draft),
      )
      self._active = record
      self._active_control = control

    thread = threading.Thread(
        target=self._run_thread, args=(draft, record, control), daemon=True
    )
    thread.start()
    return record

  def status(self) -> dict[str, Any]:
    with self._lock:
      active = self._active.to_dict() if self._active else None
      control = self._active_control
      control_state = self._control_state(control) if control else None
    return {
        "active": active,
        "control": control_state,
        "recent_runs": self.list_runs(),
    }

  def control(self, command: str) -> dict[str, Any]:
    with self._lock:
      control = self._active_control
    if control is None:
      raise RuntimeError("No active run control is available.")
    if command == "play":
      control.step_controller.play()
    elif command == "pause":
      control.step_controller.pause()
    elif command == "step":
      control.step_controller.step()
    elif command == "stop":
      control.step_controller.stop()
    else:
      raise ValueError(f"Unknown command: {command}")
    return {
        "status": "ok",
        "command": command,
        "control": self._control_state(control),
    }

  def list_runs(self) -> list[dict[str, Any]]:
    if not self._paths.runs_dir.exists():
      return []
    runs = []
    for path in sorted(self._paths.runs_dir.iterdir(), reverse=True):
      if not path.is_dir():
        continue
      manifest = path / "manifest.json"
      if manifest.exists():
        try:
          runs.append(
              _enrich_run_manifest(
                  path, json.loads(manifest.read_text(encoding="utf-8"))
              )
          )
          continue
        except json.JSONDecodeError:
          pass
      runs.append(
          _enrich_run_manifest(
              path, {"run_id": path.name, "run_dir": str(path)}
          )
      )
    return runs[:20]

  def delete_run(self, run_id: str) -> dict[str, Any]:
    run_dir = _safe_run_dir(self._paths.runs_dir, run_id)
    with self._lock:
      if (
          self._active
          and self._active.run_id == run_id
          and self._active.status in ("starting", "running")
      ):
        raise RuntimeError(f"Run {run_id} is active and cannot be deleted.")
    if not run_dir.exists() or not run_dir.is_dir():
      raise FileNotFoundError(f"Run {run_id} does not exist.")
    shutil.rmtree(run_dir)
    with self._lock:
      if self._active and self._active.run_id == run_id:
        self._active = None
        self._active_control = None
    return {"status": "deleted", "run_id": run_id}

  def _run_thread(
      self,
      draft: dict[str, Any],
      record: RunRecord,
      control: simulation_server.SimulationServer,
  ) -> None:
    with self._lock:
      record.status = "running"
    try:
      snapshot = config_io.snapshot_for_run(draft, record.run_id)
      record.run_dir.mkdir(parents=True, exist_ok=True)
      config_io.write_json(record.run_dir / "config_snapshot.json", snapshot)

      config = config_io.build_config(snapshot)
      config_html = visual_interface.visualize_config_to_html(
          config, title=f"Loveline Debug {record.run_id}"
      )
      (record.run_dir / "config_visualization.html").write_text(
          config_html, encoding="utf-8"
      )

      model = self._build_model(snapshot["run"])
      sim = simulation.Simulation(
          config=config,
          model=model,
          embedder=config_io.deterministic_embedder,
      )
      _install_json_safe_checkpointing(sim)
      control.set_simulation(sim)
      checkpoint_dir = record.run_dir / "checkpoints"
      control.broadcast_entity_info(sim.make_checkpoint_data())

      log = sim.play(
          max_steps=int(snapshot["run"].get("max_steps") or 8),
          checkpoint_path=(
              str(checkpoint_dir)
              if snapshot["run"].get("checkpoint_every_step", True)
              else None
          ),
          step_controller=control.step_controller,
          step_callback=lambda step: self._on_step(record, control, step),
      )

      json_path = record.run_dir / "structured_log.json"
      html_path = record.run_dir / "log.html"
      json_path.write_text(log.to_json(), encoding="utf-8")
      html_path.write_text(log.to_html(), encoding="utf-8")
      record.artifacts = {
          "config_snapshot": str(record.run_dir / "config_snapshot.json"),
          "structured_log": str(json_path),
          "html_log": str(html_path),
          "config_visualization": str(record.run_dir / "config_visualization.html"),
          "checkpoints": str(checkpoint_dir),
      }
      if control.step_controller.should_stop():
        record.status = "stopped"
      else:
        record.status = "completed"
        control.broadcast_completion()
    except Exception as exc:  # pylint: disable=broad-exception-caught
      record.status = "failed"
      record.error = f"{exc}\n{traceback.format_exc()}"
    finally:
      record.finished_at = dt.datetime.now(dt.timezone.utc).isoformat()
      self._write_manifest(record)
      with self._lock:
        if self._active_control is control:
          self._active_control = None

  def _build_model(self, run_settings: dict[str, Any]):
    if run_settings.get("disable_language_model", False):
      return no_language_model.NoLanguageModel()
    return language_model_setup.setup(
        api_type=run_settings.get("api_type") or config_io.DEFAULT_API_TYPE,
        model_name=run_settings.get("model_name") or config_io.DEFAULT_MODEL_NAME,
        api_key=run_settings.get("api_key") or None,
        disable_language_model=False,
    )

  def _on_step(
      self,
      record: RunRecord,
      control: simulation_server.SimulationServer,
      step_data: Any,
  ) -> None:
    control.broadcast_step(step_data)
    record.current_step = step_data.step
    record.transcript.append({
        "step": step_data.step,
        "acting_entity": step_data.acting_entity,
        "action": step_data.action,
        "entity_actions": step_data.entity_actions,
    })
    self._write_status(record)

  def _write_status(self, record: RunRecord) -> None:
    config_io.write_json(record.run_dir / "status.json", record.to_dict())

  def _write_manifest(self, record: RunRecord) -> None:
    manifest = record.to_dict()
    manifest.pop("transcript", None)
    config_io.write_json(record.run_dir / "manifest.json", manifest)
    self._write_status(record)

  @staticmethod
  def _control_state(
      control: simulation_server.SimulationServer,
  ) -> dict[str, Any]:
    is_running = control.step_controller.is_running
    is_paused = control.step_controller.is_paused
    if control.step_controller.should_stop():
      is_running = False
      is_paused = True
    return {
        "is_running": is_running,
        "is_paused": is_paused,
        "current_step": control.current_step_data.get("step", 0),
        "state": "playing"
        if is_running
        else "paused",
    }


def _json_safe(value: Any, seen: set[int] | None = None) -> Any:
  """Converts Concordia run callback data into JSON-serializable values."""
  if value is None or isinstance(value, (bool, int, float, str)):
    return value
  if isinstance(value, Path):
    return str(value)
  if seen is None:
    seen = set()
  value_id = id(value)
  if value_id in seen:
    return repr(value)

  if dataclasses.is_dataclass(value) and not isinstance(value, type):
    seen.add(value_id)
    try:
      return {
          field.name: _json_safe(getattr(value, field.name), seen)
          for field in dataclasses.fields(value)
      }
    finally:
      seen.remove(value_id)

  if isinstance(value, collections.abc.Mapping):
    seen.add(value_id)
    try:
      return {
          str(_json_safe(key, seen)): _json_safe(item, seen)
          for key, item in value.items()
      }
    finally:
      seen.remove(value_id)

  if isinstance(value, tuple) and hasattr(value, "_asdict"):
    return _json_safe(value._asdict(), seen)

  if isinstance(value, collections.abc.Sequence) and not isinstance(
      value, (str, bytes, bytearray)
  ):
    seen.add(value_id)
    try:
      return [_json_safe(item, seen) for item in value]
    finally:
      seen.remove(value_id)

  return repr(value)


def _enrich_run_manifest(run_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
  """Adds artifact and config metadata from files already in the run directory."""
  enriched = dict(manifest)
  artifacts = dict(enriched.get("artifacts") or {})
  for key, filename in (
      ("config_snapshot", "config_snapshot.json"),
      ("structured_log", "structured_log.json"),
      ("html_log", "log.html"),
      ("config_visualization", "config_visualization.html"),
      ("status", "status.json"),
  ):
    path = run_dir / filename
    if path.exists() and key not in artifacts:
      artifacts[key] = str(path)
  if artifacts:
    enriched["artifacts"] = artifacts

  snapshot_path = run_dir / "config_snapshot.json"
  if snapshot_path.exists():
    try:
      snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
      snapshot = {}
    summary = _draft_summary(snapshot)
    summary["snapshot_at"] = snapshot.get("snapshot_at")
    enriched["summary"] = {**summary, **(enriched.get("summary") or {})}
  return enriched


def _safe_run_dir(runs_root: Path, run_id: str) -> Path:
  if not run_id or "/" in run_id or "\\" in run_id:
    raise ValueError("Run id must be a single saved run directory name.")
  run_dir = runs_root / run_id
  if run_dir.is_symlink():
    raise ValueError("Run directory symlinks cannot be deleted.")
  resolved = run_dir.resolve()
  root = runs_root.resolve()
  if resolved.parent != root:
    raise ValueError("Run path is outside the Loveline runs directory.")
  return run_dir


def _draft_summary(draft: dict[str, Any]) -> dict[str, Any]:
  """Returns compact run context for UI history and manifests."""
  contestants = draft.get("contestants") or []
  run = draft.get("run") or {}
  scene_types = draft.get("scene_types") or {}
  scenes = []
  total_rounds = 0
  for index, scene in enumerate(draft.get("scenes") or []):
    rounds = scene.get("num_rounds") or scene_types.get(scene.get("type"), {}).get(
        "rounds"
    )
    if rounds:
      total_rounds += int(rounds)
    scenes.append({
        "index": index,
        "id": scene.get("id") or f"Scene {index + 1}",
        "type": scene.get("type"),
        "rounds": rounds,
        "participants": scene.get("participants") or [],
    })
  return {
      "selected_pair": [
          item.get("name") for item in contestants if item.get("name")
      ],
      "candidates": [
          item.get("name") for item in contestants if item.get("name")
      ],
      "selected_candidate_ids": draft.get("selected_candidate_ids") or [],
      "source_root": draft.get("source_root"),
      "scene_count": len(draft.get("scenes") or []),
      "total_configured_rounds": total_rounds,
      "show_flow": scenes,
      "max_steps": run.get("max_steps"),
      "disable_language_model": bool(run.get("disable_language_model")),
      "api_type": run.get("api_type"),
      "model_name": run.get("model_name"),
      "model": run.get("model_name"),
      "start_paused": run.get("start_paused", True) is not False,
      "checkpoint_every_step": run.get("checkpoint_every_step", True) is not False,
  }


def _install_json_safe_checkpointing(sim: Any) -> None:
  """Ensures Loveline debug checkpoints survive stock JSON checkpoint writes."""
  make_checkpoint_data = sim.make_checkpoint_data

  def make_json_safe_checkpoint_data() -> dict[str, Any]:
    return _json_safe(make_checkpoint_data())

  sim.make_checkpoint_data = make_json_safe_checkpoint_data
