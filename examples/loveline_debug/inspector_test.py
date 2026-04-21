"""Tests for Loveline structured-log turn inspector parsing."""

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


if __name__ == "__main__":
  unittest.main()
