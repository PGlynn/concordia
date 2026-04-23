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
                "Instructions": {
                    "Key": "Instructions",
                    "Value": (
                        "The instructions for how to play the role of Alex are "
                        "as follows. Keep Alex grounded and realistic."
                    ),
                },
                "Goal": {"Key": "Goal", "Value": "Find a serious match."},
                "Situation": {"Key": "Situation", "Value": "Alex is in a pod."},
                "SituationPerception": {
                    "Key": "SituationPerception",
                    "State": "Alex is currently in a pod date.",
                    "Prompt": "What situation is Alex in right now?",
                },
                "SelfPerception": {
                    "Key": "SelfPerception",
                    "State": "Alex is reflective and cautious.",
                    "Prompt": "What kind of person is Alex?",
                },
                "PersonBySituation": {
                    "Key": "PersonBySituation",
                    "State": "Alex would answer with reassurance.",
                    "Prompt": (
                        "What would a person like Alex do in a situation like "
                        "this?"
                    ),
                },
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
    (run_dir / "config_snapshot.json").write_text(
        json.dumps({
            "contestants": [{
                "name": "Alex",
                "player_specific_context": "Alex entered the show after a long engagement ended.",
                "player_specific_memories": [
                    "Alex wants marriage.",
                    "Alex hates performative flirting.",
                ],
            }],
            "scene_types": {
                "pod_date": {
                    "rounds": 3,
                    "call_to_action": "Answer the pod opener with honesty and warmth.",
                    "context_override": "Keep the scene tentative and intimate.",
                    "memory_filter": "marriage\npod",
                }
            },
            "scenes": [{
                "id": "pod_1",
                "type": "pod_date",
                "participants": ["Alex", "Blake"],
                "premise": {
                    "Alex": ["Alex is hearing Blake through the wall for the first time."],
                },
            }],
        }),
        encoding="utf-8",
    )

    payload = inspector.load_run_inspector(run_dir)

    self.assertTrue(payload["available"])
    self.assertEqual(payload["entries"][0]["entity_name"], "Alex")
    selected = payload["selected"]
    self.assertEqual(selected["action"], "I am here for something real.")
    self.assertEqual(
        selected["raw_utterance_text"], "I am here for something real."
    )
    self.assertEqual(
        selected["concordia_event_text"],
        "Alex: I am here for something real.",
    )
    self.assertEqual(
        selected["observations"], ["[observation] Blake asked about commitment."]
    )
    self.assertIn({"name": "Goal", "value": "Find a serious match."}, selected["components"])
    self.assertEqual(
        [item["name"] for item in selected["stock_key_questions"]],
        ["SituationPerception", "SelfPerception", "PersonBySituation"],
    )
    self.assertEqual(
        selected["stock_key_questions"][1]["value"],
        "Alex is reflective and cautious.",
    )
    self.assertEqual(
        selected["stock_key_questions"][2]["prompt"],
        "What would a person like Alex do in a situation like this?",
    )
    self.assertEqual(selected["entity_memories"], ["Alex wants marriage."])
    self.assertEqual(selected["game_master_memories"], ["The pod date started."])
    self.assertEqual(
        selected["game_master_entries"][0]["data"]["event_resolution"]["Value"],
        "Blake hears Alex's answer.",
    )
    self.assertIn(
        "The instructions for how to play the role of Alex are as follows.",
        selected["active_inputs"]["instructions"],
    )
    self.assertEqual(
        selected["active_inputs"]["goal"], "Find a serious match."
    )
    self.assertEqual(
        selected["active_inputs"]["call_to_action"],
        "Answer the pod opener with honesty and warmth.",
    )
    self.assertEqual(
        selected["active_inputs"]["scene_premise"],
        ["Alex is hearing Blake through the wall for the first time."],
    )
    self.assertEqual(
        selected["active_inputs"]["loaded_context"][0]["value"],
        "Alex entered the show after a long engagement ended.",
    )
    self.assertEqual(
        selected["active_inputs"]["loaded_memories"][0]["value"],
        ["Alex wants marriage.", "Alex hates performative flirting."],
    )
    self.assertEqual(
        selected["active_inputs"]["loaded_memories"][1]["value"],
        ["Alex wants marriage."],
    )
    self.assertEqual(selected["active_inputs"]["scene"]["round"], 3)

  def test_stock_key_question_outputs_read_state_from_real_log_shape(self):
    raw_entry_data = {
        "key": "Entity [Marcus Vale]",
        "value": {
            "SituationPerception": {
                "Key": "Question: What situation is Marcus Vale in right now?",
                "Summary": "Marcus is in a pod date.",
                "State": "Marcus is on a blind pod date with Lena.",
            },
            "SelfPerception": {
                "Key": "Question: What kind of person is Marcus Vale?",
                "Summary": "Marcus sees himself as intentional.",
                "State": "Marcus is direct, warm, and looking for commitment.",
            },
            "PersonBySituation": {
                "Key": (
                    "Question: What would a person like Marcus Vale do in a "
                    "situation like this?"
                ),
                "Summary": "Marcus asks a careful opening question.",
                "State": "Marcus would ask Lena what made her smile today.",
            },
        },
    }

    rows = inspector._stock_key_question_outputs(raw_entry_data)

    self.assertEqual(
        [item["name"] for item in rows],
        ["SituationPerception", "SelfPerception", "PersonBySituation"],
    )
    self.assertEqual(
        rows[0]["value"], "Marcus is on a blind pod date with Lena."
    )
    self.assertEqual(
        rows[1]["value"],
        "Marcus is direct, warm, and looking for commitment.",
    )
    self.assertEqual(
        rows[2]["summary"], "Marcus asks a careful opening question."
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
    self.assertIn(
        "deduplicated and reconstructed",
        payload["entries"][0]["raw_utterance_text"],
    )
    self.assertIn(
        "Alex: This answer is intentionally long enough",
        payload["entries"][0]["concordia_event_text"],
    )
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
    self.assertEqual(
        payload["right"]["first_turn"]["raw_utterance_text"], "I need more time."
    )
    self.assertEqual(
        payload["right"]["first_turn"]["concordia_event_text"],
        "Blake: I need more time.",
    )
    self.assertEqual(payload["left"]["transcript"][0]["action"], "I am ready.")
    diff_labels = {item["label"] for item in payload["diffs"]}
    self.assertIn("First Actor", diff_labels)
    self.assertIn("First Action", diff_labels)
    self.assertIn("First Raw Utterance", diff_labels)
    self.assertIn("First Concordia Event", diff_labels)

  def test_prefixed_action_is_split_into_raw_and_display_text(self):
    run_dir = Path(tempfile.mkdtemp())
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
                    "Value": "Alex: I already include the Concordia prefix.",
                },
            },
        },
    )
    (run_dir / "structured_log.json").write_text(log.to_json(), encoding="utf-8")

    payload = inspector.load_run_inspector(run_dir)

    selected = payload["selected"]
    self.assertEqual(
        selected["raw_utterance_text"],
        "I already include the Concordia prefix.",
    )
    self.assertEqual(
        selected["concordia_event_text"],
        "Alex: I already include the Concordia prefix.",
    )

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
