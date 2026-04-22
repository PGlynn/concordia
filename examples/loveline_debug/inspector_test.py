"""Tests for Loveline structured-log turn inspector parsing."""

import json
from pathlib import Path
import tempfile
import unittest

from concordia.utils import structured_logging
from examples.loveline_debug import inspector


class InspectorTest(unittest.TestCase):

  def test_load_run_inspector_surfaces_turn_context(self):
    run_dir = Path(tempfile.mkdtemp())
    log = structured_logging.SimulationLog()
    log.add_entry(
        step=3,
        timestamp="2026-04-21T22:00:00+00:00",
        entity_name="Alex",
        component_name="entity_action",
        entry_type="entity",
        summary="Step 3 Alex speaks",
        raw_data={
            "key": "Entity [Alex]",
            "value": {
                "Goal": {"Key": "Goal", "Value": "Find a serious match."},
                "Situation": {"Key": "Situation", "Value": "Alex is in a pod."},
                "__observation__": {
                    "Key": "Observation",
                    "Value": ["[observation] Blake asked about commitment."],
                },
                "__act__": {
                    "Summary": "Action: Alex answers",
                    "Value": "I am here for something real.",
                    "Prompt": ["Instructions:", "Answer honestly."],
                },
            },
        },
    )
    log.add_entry(
        step=3,
        timestamp="2026-04-21T22:00:01+00:00",
        entity_name="Show Runner",
        component_name="game_master",
        entry_type="step",
        summary="Show Runner resolves Alex",
        raw_data={
            "key": "Show Runner --- Event: Alex",
            "value": {
                "event_resolution": {
                    "Value": "Blake hears Alex's answer.",
                    "Prompt": "Resolve the spoken line.",
                    "Summary": "Blake heard sincerity.",
                }
            },
        },
    )
    log.attach_memories(
        entity_memories={"Alex": ["Alex wants marriage."]},
        game_master_memories=["The pod date started."],
    )
    (run_dir / "structured_log.json").write_text(log.to_json(), encoding="utf-8")

    payload = inspector.load_run_inspector(run_dir)

    self.assertTrue(payload["available"])
    self.assertEqual(payload["entries"][0]["entity_name"], "Alex")
    selected = payload["selected"]
    self.assertEqual(selected["action"], "I am here for something real.")
    self.assertEqual(
        selected["observations"], ["[observation] Blake asked about commitment."]
    )
    self.assertIn({"name": "Goal", "value": "Find a serious match."}, selected["components"])
    self.assertEqual(selected["entity_memories"], ["Alex wants marriage."])
    self.assertEqual(selected["game_master_memories"], ["The pod date started."])
    self.assertEqual(
        selected["game_master_entries"][0]["data"]["event_resolution"]["Value"],
        "Blake hears Alex's answer.",
    )

  def test_missing_structured_log_reports_unavailable(self):
    run_dir = Path(tempfile.mkdtemp())

    payload = inspector.load_run_inspector(run_dir)

    self.assertFalse(payload["available"])
    self.assertEqual(payload["run_id"], run_dir.name)
    self.assertEqual(payload["entries"], [])

  def test_load_log_browser_returns_reconstructed_entries_and_artifacts(self):
    run_dir = Path(tempfile.mkdtemp()) / "run_with_log"
    run_dir.mkdir()
    log = structured_logging.SimulationLog()
    log.add_entry(
        step=1,
        timestamp="2026-04-21T22:00:00+00:00",
        entity_name="Alex",
        component_name="entity_action",
        entry_type="entity",
        summary="Alex speaks",
        raw_data={
            "key": "Entity [Alex]",
            "value": {
                "__act__": {
                    "Summary": "Action: Alex speaks",
                    "Value": "This answer is intentionally long enough to be deduplicated and reconstructed.",
                },
            },
        },
    )
    (run_dir / "structured_log.json").write_text(log.to_json(), encoding="utf-8")
    (run_dir / "log.html").write_text("<html>log</html>", encoding="utf-8")

    payload = inspector.load_log_browser(run_dir)

    self.assertTrue(payload["available"])
    self.assertEqual(payload["entry_count"], 1)
    self.assertEqual(payload["entries"][0]["entity_name"], "Alex")
    self.assertIn("deduplicated and reconstructed", payload["entries"][0]["preview"])
    raw_value = payload["entries"][0]["raw_entry"]["data"]["value"]["__act__"][
        "Value"
    ]
    self.assertIn("intentionally long enough", raw_value)
    self.assertEqual(payload["artifacts"]["html_log"], str(run_dir / "log.html"))

  def test_load_first_turn_compare_uses_run_artifacts(self):
    left_dir = Path(tempfile.mkdtemp()) / "left_run"
    right_dir = Path(tempfile.mkdtemp()) / "right_run"
    left_dir.mkdir()
    right_dir.mkdir()
    self._write_compare_artifacts(left_dir, "Alex", "I am ready.")
    self._write_compare_artifacts(right_dir, "Blake", "I need more time.")

    payload = inspector.load_first_turn_compare(left_dir, right_dir)

    self.assertTrue(payload["available"])
    self.assertEqual(payload["left"]["config"]["candidates"], ["Alex", "Blake"])
    self.assertEqual(payload["left"]["first_turn"]["entity_name"], "Alex")
    self.assertEqual(payload["right"]["first_turn"]["action"], "I need more time.")
    self.assertEqual(payload["left"]["transcript"][0]["action"], "I am ready.")
    diff_labels = {item["label"] for item in payload["diffs"]}
    self.assertIn("First Actor", diff_labels)
    self.assertIn("First Action", diff_labels)

  def _write_compare_artifacts(
      self,
      run_dir: Path,
      actor: str,
      action: str,
  ) -> None:
    log = structured_logging.SimulationLog()
    log.add_entry(
        step=1,
        timestamp="2026-04-21T22:00:00+00:00",
        entity_name=actor,
        component_name="entity_action",
        entry_type="entity",
        summary=f"{actor} speaks",
        raw_data={
            "key": f"Entity [{actor}]",
            "value": {
                "Goal": {"Key": "Goal", "Value": "Find a match."},
                "__act__": {
                    "Summary": f"Action: {actor} speaks",
                    "Value": action,
                    "Prompt": ["Answer the prompt."],
                },
            },
        },
    )
    (run_dir / "structured_log.json").write_text(log.to_json(), encoding="utf-8")
    (run_dir / "config_snapshot.json").write_text(
        json.dumps({
            "contestants": [{"name": "Alex"}, {"name": "Blake"}],
            "selected_candidate_ids": ["alex", "blake"],
            "scenes": [{"id": "scene_1"}],
            "scene_defaults": {"main_game_master_name": "Show Runner"},
            "run": {
                "max_steps": 8,
                "model_name": "test",
                "disable_language_model": True,
            },
        }),
        encoding="utf-8",
    )
    (run_dir / "status.json").write_text(
        json.dumps({
            "transcript": [{
                "step": 1,
                "acting_entity": actor,
                "action": action,
            }]
        }),
        encoding="utf-8",
    )


if __name__ == "__main__":
  unittest.main()
