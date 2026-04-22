"""Smoke tests for the Loveline debug config path."""

from pathlib import Path

from absl.testing import absltest

from concordia.associative_memory import basic_associative_memory
from concordia.language_model import no_language_model
from concordia.typing import prefab as prefab_lib
from examples.loveline_debug import basic_entity_controls
from examples.loveline_debug import config_io


def _embedder(text: str):
  del text
  return [0.0, 0.0, 0.0]


class ConfigIoTest(absltest.TestCase):

  def test_default_draft_is_exactly_one_man_and_one_woman(self):
    draft = config_io.make_default_draft()

    config_io.validate_draft(draft)
    self.assertLen(draft["contestants"], 2)
    self.assertEqual(
        sorted(item["gender"] for item in draft["contestants"]),
        ["man", "woman"],
    )

  def test_default_draft_enables_lm_and_points_to_local_model(self):
    draft = config_io.make_default_draft()

    self.assertFalse(draft["run"]["disable_language_model"])
    self.assertEqual(draft["run"]["api_type"], "ollama")
    self.assertEqual(draft["run"]["model_name"], "qwen3.5:35b-a3b")

  def test_default_draft_exposes_stock_basic_entity_history_lengths(self):
    draft = config_io.make_default_draft()

    for contestant in draft["contestants"]:
      self.assertContainsSubset(
          config_io.BASIC_ENTITY_HISTORY_LENGTH_DEFAULTS,
          contestant["entity_params"],
      )

  def test_default_draft_exposes_stock_basic_entity_component_toggles(self):
    draft = config_io.make_default_draft()

    for contestant in draft["contestants"]:
      self.assertEqual(
          contestant["entity_params"]["stock_basic_entity_components"],
          config_io.STOCK_BASIC_ENTITY_COMPONENT_DEFAULTS,
      )

  def test_build_config_uses_stock_roles_and_two_entities(self):
    draft = config_io.make_default_draft()

    config = config_io.build_config(draft)

    entity_instances = [
        item for item in config.instances if item.role == prefab_lib.Role.ENTITY
    ]
    gm_instances = [
        item
        for item in config.instances
        if item.role == prefab_lib.Role.GAME_MASTER
    ]
    initializer_instances = [
        item
        for item in config.instances
        if item.role == prefab_lib.Role.INITIALIZER
    ]
    self.assertLen(entity_instances, 2)
    self.assertLen(gm_instances, 1)
    self.assertLen(initializer_instances, 1)
    self.assertEqual(
        {item.prefab for item in entity_instances},
        {"basic__Entity"},
    )
    self.assertIn("dialogic_and_dramaturgic__GameMaster", config.prefabs)
    self.assertIn("formative_memories_initializer__GameMaster", config.prefabs)
    self.assertIsInstance(
        config.prefabs["basic__Entity"], basic_entity_controls.Entity
    )

  def test_history_lengths_persist_through_draft_json_and_config_params(self):
    draft = config_io.make_default_draft()
    draft["contestants"][0]["entity_params"].update({
        "observation_history_length": 7,
        "situation_perception_history_length": 8,
        "self_perception_history_length": 9,
        "person_by_situation_history_length": 10,
    })
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))

    config_io.save_draft(draft, "history_lengths", paths)
    loaded = config_io.load_draft("history_lengths", paths)
    config = config_io.build_config(loaded)

    self.assertEqual(
        loaded["contestants"][0]["entity_params"][
            "observation_history_length"
        ],
        7,
    )
    entity_instances = [
        item for item in config.instances if item.role == prefab_lib.Role.ENTITY
    ]
    self.assertEqual(
        entity_instances[0].params,
        loaded["contestants"][0]["entity_params"],
    )

  def test_component_toggles_persist_through_draft_json_and_config_params(self):
    draft = config_io.make_default_draft()
    draft["contestants"][0]["entity_params"][
        "stock_basic_entity_components"
    ] = {
        "SituationPerception": False,
        "SelfPerception": True,
        "PersonBySituation": False,
    }
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))

    config_io.save_draft(draft, "component_toggles", paths)
    loaded = config_io.load_draft("component_toggles", paths)
    config = config_io.build_config(loaded)

    entity_instances = [
        item for item in config.instances if item.role == prefab_lib.Role.ENTITY
    ]
    self.assertEqual(
        entity_instances[0].params["stock_basic_entity_components"],
        {
            "SituationPerception": False,
            "SelfPerception": True,
            "PersonBySituation": False,
        },
    )

  def test_debug_basic_entity_build_omits_disabled_question_components(self):
    entity_config = basic_entity_controls.Entity(
        params={
            "name": "Alex",
            "stock_basic_entity_components": {
                "SituationPerception": False,
                "SelfPerception": True,
                "PersonBySituation": False,
            },
        }
    )

    entity = entity_config.build(
        model=no_language_model.NoLanguageModel(),
        memory_bank=basic_associative_memory.AssociativeMemoryBank(
            sentence_embedder=_embedder
        ),
    )

    components = entity.get_all_context_components()
    self.assertNotIn("SituationPerception", components)
    self.assertIn("SelfPerception", components)
    self.assertNotIn("PersonBySituation", components)
    self.assertEqual(
        entity.get_act_component().get_context_concat_order(),
        (
            "Instructions",
            "Observation",
            "SelfPerception",
            "__observation__",
            "__memory__",
        ),
    )

  def test_rejects_two_candidates_with_same_gender(self):
    source = config_io.list_source_data()
    men = [item for item in source["candidates"] if item["gender"] == "man"]
    draft = config_io.make_draft_for_selection([men[0]["id"], men[1]["id"]])

    with self.assertRaises(config_io.DraftValidationError):
      config_io.validate_draft(draft)


if __name__ == "__main__":
  absltest.main()
