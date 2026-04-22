"""Smoke tests for Loveline debug run-control status."""

import json
from pathlib import Path

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
        "source_root": "/tmp/starter",
        "selected_candidate_ids": ["alex_id", "blake_id"],
        "contestants": [{"name": "Alex"}, {"name": "Blake"}],
        "scenes": [{"id": "pod"}],
        "run": {
            "max_steps": 12,
            "disable_language_model": True,
            "api_type": "openai",
            "model_name": "gpt-4o-mini",
            "start_paused": False,
            "checkpoint_every_step": False,
        },
    }

    summary = runner._draft_summary(draft)  # pylint: disable=protected-access

    self.assertEqual(summary["selected_pair"], ["Alex", "Blake"])
    self.assertEqual(summary["selected_candidate_ids"], ["alex_id", "blake_id"])
    self.assertEqual(summary["scene_count"], 1)
    self.assertEqual(summary["max_steps"], 12)
    self.assertTrue(summary["disable_language_model"])
    self.assertFalse(summary["start_paused"])
    self.assertFalse(summary["checkpoint_every_step"])


if __name__ == "__main__":
  absltest.main()
