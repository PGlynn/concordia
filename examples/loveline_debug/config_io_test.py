"""Smoke tests for the Loveline debug config path."""

from absl.testing import absltest

from concordia.typing import prefab as prefab_lib
from examples.loveline_debug import config_io


class ConfigIoTest(absltest.TestCase):

  def test_default_draft_is_exactly_one_man_and_one_woman(self):
    draft = config_io.make_default_draft()

    config_io.validate_draft(draft)
    self.assertLen(draft["contestants"], 2)
    self.assertEqual(
        sorted(item["gender"] for item in draft["contestants"]),
        ["man", "woman"],
    )

  def test_default_draft_keeps_smoke_lm_disabled_but_points_to_local_model(self):
    draft = config_io.make_default_draft()

    self.assertTrue(draft["run"]["disable_language_model"])
    self.assertEqual(draft["run"]["api_type"], "ollama")
    self.assertEqual(draft["run"]["model_name"], "qwen3.5:35b-a3b")

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

  def test_rejects_two_candidates_with_same_gender(self):
    source = config_io.list_source_data()
    men = [item for item in source["candidates"] if item["gender"] == "man"]
    draft = config_io.make_draft_for_selection([men[0]["id"], men[1]["id"]])

    with self.assertRaises(config_io.DraftValidationError):
      config_io.validate_draft(draft)


if __name__ == "__main__":
  absltest.main()
