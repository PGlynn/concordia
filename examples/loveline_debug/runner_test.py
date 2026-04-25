"""Smoke tests for Loveline debug run-control status."""

import json
from pathlib import Path
from types import SimpleNamespace

from absl.testing import absltest

from concordia.typing import entity as entity_lib
from concordia.typing import scene as scene_lib
from concordia.utils import simulation_server
from examples.loveline_debug import config_io
from examples.loveline_debug import runner


class RunnerTest(absltest.TestCase):

  def test_status_serializes_transcript_with_concordia_scene_spec(self):
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))
    manager = runner.RunManager(paths)
    scene_type = scene_lib.SceneTypeSpec(
        name="date",
        game_master_name="Show Runner",
        action_spec=entity_lib.free_action_spec(
            call_to_action="Say something charming."
        ),
    )
    record = runner.RunRecord(
        run_id="run",
        status="running",
        run_dir=paths.runs_dir / "run",
        started_at="2026-04-21T00:00:00+00:00",
        transcript=[{
            "step": 1,
            "acting_entity": "Alex",
            "action": "waves",
            "entity_actions": {"Alex": scene_type},
        }],
    )
    manager._active = record  # pylint: disable=protected-access

    payload = manager.status()

    json.dumps(payload)
    self.assertIsInstance(
        payload["active"]["transcript"][0]["entity_actions"]["Alex"],
        dict,
    )

  def test_delete_run_removes_saved_artifacts(self):
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))
    manager = runner.RunManager(paths)
    run_dir = paths.runs_dir / "run_1"
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text("{}", encoding="utf-8")
    (run_dir / "structured_log.json").write_text("[]", encoding="utf-8")

    payload = manager.delete_run("run_1")

    self.assertEqual(payload, {"status": "deleted", "run_id": "run_1"})
    self.assertFalse(run_dir.exists())

  def test_delete_run_rejects_path_escape_and_active_run(self):
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))
    manager = runner.RunManager(paths)
    run_dir = paths.runs_dir / "run_1"
    run_dir.mkdir(parents=True)
    manager._active = runner.RunRecord(  # pylint: disable=protected-access
        run_id="run_1",
        status="running",
        run_dir=run_dir,
        started_at="2026-04-21T00:00:00+00:00",
    )

    with self.assertRaisesRegex(ValueError, "single saved run directory"):
      manager.delete_run("../run_1")
    with self.assertRaisesRegex(RuntimeError, "active"):
      manager.delete_run("run_1")
    self.assertTrue(run_dir.exists())

  def test_checkpoint_wrapper_preserves_plain_json_checkpoint_write(self):
    scene_type = scene_lib.SceneTypeSpec(
        name="date",
        game_master_name="Show Runner",
        action_spec=entity_lib.free_action_spec(
            call_to_action="Say something charming."
        ),
    )

    class FakeSimulation:

      def make_checkpoint_data(self):
        return {
            "entities": {},
            "game_masters": {
                "Show Runner": {
                    "components": {
                        "scene_type": scene_type,
                    },
                },
            },
            "raw_log": [{"scene_type": scene_type}],
        }

      def save_checkpoint(self, path: Path):
        checkpoint_data = self.make_checkpoint_data()
        with path.open("w", encoding="utf-8") as handle:
          json.dump(checkpoint_data, handle, indent=2)

    sim = FakeSimulation()
    runner._install_json_safe_checkpointing(sim)  # pylint: disable=protected-access
    checkpoint_path = Path(self.create_tempdir().full_path) / "checkpoint.json"

    sim.save_checkpoint(checkpoint_path)
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))

    scene_type_payload = checkpoint["game_masters"]["Show Runner"][
        "components"
    ]["scene_type"]
    self.assertEqual(scene_type_payload["name"], "date")
    self.assertEqual(checkpoint["raw_log"][0]["scene_type"]["name"], "date")

  def test_stop_control_response_reports_paused_state(self):
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))
    manager = runner.RunManager(paths)
    control = simulation_server.SimulationServer(html_content="")
    manager._active_control = control  # pylint: disable=protected-access

    response = manager.control("stop")

    self.assertFalse(response["control"]["is_running"])
    self.assertTrue(response["control"]["is_paused"])
    self.assertEqual(response["control"]["state"], "paused")

  def test_draft_summary_captures_pair_and_run_settings(self):
    draft = {
        "name": "alex_blake_debug",
        "source_root": "/tmp/starter",
        "selected_candidate_ids": ["alex_id", "blake_id"],
        "contestants": [{"name": "Alex"}, {"name": "Blake"}],
        "scene_types": {"pod_date": {"rounds": 2}},
        "scenes": [{"id": "pod", "type": "pod_date"}],
        "run": {
            "max_steps": 12,
            "disable_language_model": True,
            "model_preset": "codex_oauth",
            "api_type": "ollama",
            "model_name": "qwen3.5:35b-a3b",
            "start_paused": False,
            "checkpoint_every_step": False,
            "skip_generated_formative_memories": True,
            "strict_candidate_fact_anchoring": True,
        },
    }

    summary = runner._draft_summary(draft)  # pylint: disable=protected-access

    self.assertEqual(summary["draft_name"], "alex_blake_debug")
    self.assertEqual(summary["name"], "alex_blake_debug")
    self.assertEqual(summary["selected_pair"], ["Alex", "Blake"])
    self.assertEqual(summary["selected_candidate_ids"], ["alex_id", "blake_id"])
    self.assertEqual(summary["scene_count"], 1)
    self.assertEqual(summary["total_configured_rounds"], 2)
    self.assertEqual(summary["show_flow"][0]["id"], "pod")
    self.assertEqual(summary["show_flow"][0]["rounds"], 2)
    self.assertEqual(summary["max_steps"], 12)
    self.assertTrue(summary["disable_language_model"])
    self.assertEqual(summary["model_preset"], "local_ollama")
    self.assertEqual(summary["model_preset_label"], "Local Ollama")
    self.assertFalse(summary["start_paused"])
    self.assertFalse(summary["checkpoint_every_step"])
    self.assertTrue(summary["skip_generated_formative_memories"])
    self.assertTrue(summary["strict_candidate_fact_anchoring"])

  def test_on_step_cleans_duplicate_speaker_prefix_and_preserves_raw_action(self):
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))
    manager = runner.RunManager(paths)
    record = runner.RunRecord(
        run_id="run",
        status="running",
        run_dir=paths.runs_dir / "run",
        started_at="2026-04-21T00:00:00+00:00",
    )
    class FakeControl:

      def broadcast_step(self, _step_data):
        return None

    manager._on_step(  # pylint: disable=protected-access
        record,
        FakeControl(),
        SimpleNamespace(
            step=1,
            acting_entity="Marcus Vale",
            action="Marcus Vale: Marcus Vale: I am glad you're here.",
            entity_actions={},
        ),
    )

    self.assertEqual(record.transcript[0]["action"], "I am glad you're here.")
    self.assertEqual(
        record.transcript[0]["raw_action"],
        "Marcus Vale: Marcus Vale: I am glad you're here.",
    )

  def test_model_builder_falls_back_to_local_ollama_when_lm_enabled(self):
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))
    manager = runner.RunManager(paths)
    calls = []

    def fake_setup(**kwargs):
      calls.append(kwargs)
      return object()

    original_setup = runner.language_model_setup.setup
    runner.language_model_setup.setup = fake_setup
    try:
      manager._build_model(  # pylint: disable=protected-access
          {"disable_language_model": False}
      )
    finally:
      runner.language_model_setup.setup = original_setup

    self.assertEqual(calls, [{
        "api_type": "ollama",
        "model_name": "qwen3.5:35b-a3b",
        "api_key": None,
        "disable_language_model": False,
    }])

  def test_model_builder_uses_loveline_ollama_shim_for_ollama(self):
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))
    manager = runner.RunManager(paths)
    calls = []

    class FakeLovelineOllama:

      def __init__(self, **kwargs):
        calls.append(kwargs)

    original_cls = (
        runner.language_model_setup.ollama_shim.LovelineOllamaLanguageModel
    )
    runner.language_model_setup.ollama_shim.LovelineOllamaLanguageModel = (
        FakeLovelineOllama
    )
    try:
      model = manager._build_model({  # pylint: disable=protected-access
          "disable_language_model": False,
          "api_type": "ollama",
          "model_name": "qwen3.5:35b-a3b",
      })
    finally:
      runner.language_model_setup.ollama_shim.LovelineOllamaLanguageModel = (
          original_cls
      )

    self.assertIsInstance(model, FakeLovelineOllama)
    self.assertEqual(calls, [{"model_name": "qwen3.5:35b-a3b"}])

  def test_model_builder_uses_stock_setup_for_non_ollama(self):
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))
    manager = runner.RunManager(paths)
    calls = []

    def fake_stock_setup(**kwargs):
      calls.append(kwargs)
      return "stock-model"

    original_setup = (
        runner.language_model_setup.language_models.language_model_setup
    )
    runner.language_model_setup.language_models.language_model_setup = (
        fake_stock_setup
    )
    try:
      model = manager._build_model({  # pylint: disable=protected-access
          "disable_language_model": False,
          "api_type": "openai",
          "model_name": "gpt-test",
          "api_key": "key",
      })
    finally:
      runner.language_model_setup.language_models.language_model_setup = (
          original_setup
      )

    self.assertEqual(model, "stock-model")
    self.assertEqual(
        calls,
        [{
            "api_type": "openai",
            "model_name": "gpt-test",
            "api_key": "key",
            "disable_language_model": False,
        }],
    )

  def test_run_thread_passes_entity_controls_through_snapshot_to_config(self):
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))
    manager = runner.RunManager(paths)
    draft = config_io.make_default_draft()
    draft["contestants"][0]["entity_params"].update({
        "observation_history_length": 31,
        "situation_perception_history_length": 32,
        "self_perception_history_length": 33,
        "person_by_situation_history_length": 34,
        "stock_basic_entity_components": {
            "SituationPerception": False,
            "SelfPerception": True,
            "PersonBySituation": False,
        },
    })
    draft["scene_types"]["pod_date"]["instructions_override"] = (
        "Keep the pod scene grounded and slightly guarded."
    )
    draft["scene_types"]["pod_date"]["context_override"] = (
        "Keep the pod scene focused on first impressions."
    )
    draft["scene_types"]["pod_date"]["memory_filter"] = (
        "pod\nfirst impression"
    )
    record = runner.RunRecord(
        run_id="run",
        status="queued",
        run_dir=paths.runs_dir / "run",
        started_at="2026-04-21T00:00:00+00:00",
    )
    captured_snapshots = []

    class FakeController:

      def should_stop(self):
        return False

    class FakeControl:

      step_controller = FakeController()

      def set_simulation(self, sim):
        self.sim = sim

      def broadcast_entity_info(self, payload):
        self.entity_info = payload

      def broadcast_completion(self):
        self.completed = True

    class FakeLog:

      def to_json(self):
        return "[]"

      def to_html(self):
        return "<html></html>"

    class FakeSimulation:

      def __init__(self, **kwargs):
        self.kwargs = kwargs

      def make_checkpoint_data(self):
        return {"entities": {}}

      def play(self, **kwargs):
        self.play_kwargs = kwargs
        return FakeLog()

    def fake_build_config(snapshot):
      captured_snapshots.append(snapshot)
      return "config"

    original_build_config = runner.config_io.build_config
    original_visualize = runner.visual_interface.visualize_config_to_html
    original_simulation = runner.simulation.Simulation
    runner.config_io.build_config = fake_build_config
    runner.visual_interface.visualize_config_to_html = lambda *_, **__: ""
    runner.simulation.Simulation = FakeSimulation
    try:
      manager._run_thread(  # pylint: disable=protected-access
          draft, record, FakeControl()
      )
    finally:
      runner.config_io.build_config = original_build_config
      runner.visual_interface.visualize_config_to_html = original_visualize
      runner.simulation.Simulation = original_simulation

    self.assertEqual(record.status, "completed")
    self.assertEqual(
        captured_snapshots[0]["contestants"][0]["entity_params"][
            "observation_history_length"
        ],
        31,
    )
    self.assertEqual(
        captured_snapshots[0]["contestants"][0]["entity_params"][
            "person_by_situation_history_length"
        ],
        34,
    )
    self.assertEqual(
        captured_snapshots[0]["contestants"][0]["entity_params"][
            "stock_basic_entity_components"
        ],
        {
            "SituationPerception": False,
            "SelfPerception": True,
            "PersonBySituation": False,
        },
    )
    self.assertEqual(
        captured_snapshots[0]["scene_types"]["pod_date"]["instructions_override"],
        "Keep the pod scene grounded and slightly guarded.",
    )
    self.assertEqual(
        captured_snapshots[0]["scene_types"]["pod_date"]["context_override"],
        "Keep the pod scene focused on first impressions.",
    )
    self.assertEqual(
        captured_snapshots[0]["scene_types"]["pod_date"]["memory_filter"],
        "pod\nfirst impression",
    )


if __name__ == "__main__":
  absltest.main()
