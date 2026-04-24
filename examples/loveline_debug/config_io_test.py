"""Smoke tests for the Loveline debug config path."""

import copy
from pathlib import Path
from types import SimpleNamespace

from absl.testing import absltest

from concordia.associative_memory import basic_associative_memory
from concordia.language_model import no_language_model
from concordia.typing import prefab as prefab_lib
from examples.loveline_debug import basic_entity_controls
from examples.loveline_debug import config_io
from examples.loveline_debug import scene_type_instructions


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
    self.assertFalse(draft["run"]["skip_generated_formative_memories"])

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

  def test_saved_draft_stores_selected_ids_not_contestant_copies(self):
    draft = config_io.make_default_draft()
    draft["contestants"][0]["entity_params"]["observation_history_length"] = 41
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))

    path = config_io.save_draft(draft, "shared_candidate_draft", paths)
    stored = config_io.load_json(path)
    loaded = config_io.load_draft("shared_candidate_draft", paths)

    self.assertNotIn("contestants", stored)
    self.assertEqual(stored["selected_candidate_ids"], draft["selected_candidate_ids"])
    self.assertEqual(
        loaded["contestants"][0]["entity_params"]["observation_history_length"],
        41,
    )

  def test_shared_contestant_update_hydrates_other_drafts(self):
    draft = config_io.make_default_draft()
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))
    config_io.save_draft(draft, "first", paths)
    config_io.save_draft({**draft, "name": "second"}, "second", paths)

    contestant = dict(draft["contestants"][0])
    contestant["name"] = "Edited Shared Alex"
    contestant["entity_params"] = {
        **contestant["entity_params"],
        "name": "Edited Shared Alex",
        "observation_history_length": 55,
    }
    config_io.save_contestant(contestant, paths)

    loaded = config_io.load_draft("second", paths)
    self.assertEqual(loaded["contestants"][0]["name"], "Edited Shared Alex")
    self.assertEqual(
        loaded["contestants"][0]["entity_params"]["observation_history_length"],
        55,
    )

  def test_created_shared_contestant_persists_through_save_and_reload(self):
    draft = config_io.make_default_draft()
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))

    created = config_io.create_contestant({
        **draft["contestants"][0],
        "name": "Marcus Yale",
        "entity_params": {
            **draft["contestants"][0]["entity_params"],
            "name": "Marcus Yale",
            "observation_history_length": 17,
        },
    }, paths)
    draft["contestants"][0] = created
    draft["selected_candidate_ids"] = [
        created["id"],
        draft["contestants"][1]["id"],
    ]

    path = config_io.save_draft(draft, "marcus_yale_draft", paths)
    stored = config_io.load_json(path)
    loaded = config_io.load_draft("marcus_yale_draft", paths)

    self.assertEqual(
        stored["selected_candidate_ids"],
        [created["id"], draft["contestants"][1]["id"]],
    )
    self.assertEqual(loaded["contestants"][0]["id"], created["id"])
    self.assertEqual(loaded["contestants"][0]["name"], "Marcus Yale")
    self.assertEqual(
        loaded["contestants"][0]["entity_params"]["observation_history_length"],
        17,
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

  def test_skip_generated_formative_memories_persists_and_sets_initializer(self):
    draft = config_io.make_default_draft()
    draft["run"]["skip_generated_formative_memories"] = True
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))

    config_io.save_draft(draft, "skip_formative_memories", paths)
    loaded = config_io.load_draft("skip_formative_memories", paths)
    config = config_io.build_config(loaded)

    self.assertTrue(loaded["run"]["skip_generated_formative_memories"])
    initializer = next(
        item
        for item in config.instances
        if item.role == prefab_lib.Role.INITIALIZER
    )
    self.assertEqual(
        initializer.params["skip_formative_memories_for"],
        [item["name"] for item in loaded["contestants"]],
    )

  def test_scene_type_instructions_override_persists_through_draft_json(self):
    draft = config_io.make_default_draft()
    draft["scene_types"]["pod_date"]["instructions_override"] = (
        "Run the pod date with a warmer, lighter tone."
    )
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))

    path = config_io.save_draft(draft, "scene_type_override", paths)
    stored = config_io.load_json(path)
    loaded = config_io.load_draft("scene_type_override", paths)

    self.assertEqual(
        stored["scene_types"]["pod_date"]["instructions_override"],
        "Run the pod date with a warmer, lighter tone.",
    )
    self.assertEqual(
        loaded["scene_types"]["pod_date"]["instructions_override"],
        "Run the pod date with a warmer, lighter tone.",
    )

  def test_scene_type_examples_override_persists_through_draft_json(self):
    draft = config_io.make_default_draft()
    draft["scene_types"]["pod_date"]["examples_override"] = (
        "Exercise: Keep the banter light. --- Response: A playful beat lands."
    )
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))

    path = config_io.save_draft(draft, "scene_type_examples", paths)
    stored = config_io.load_json(path)
    loaded = config_io.load_draft("scene_type_examples", paths)

    self.assertEqual(
        stored["scene_types"]["pod_date"]["examples_override"],
        "Exercise: Keep the banter light. --- Response: A playful beat lands.",
    )
    self.assertEqual(
        loaded["scene_types"]["pod_date"]["examples_override"],
        "Exercise: Keep the banter light. --- Response: A playful beat lands.",
    )

  def test_scene_type_context_override_persists_through_draft_json(self):
    draft = config_io.make_default_draft()
    draft["scene_types"]["pod_date"]["context_override"] = (
        "Treat pod scenes as fragile first-impression territory."
    )
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))

    path = config_io.save_draft(draft, "scene_type_context", paths)
    stored = config_io.load_json(path)
    loaded = config_io.load_draft("scene_type_context", paths)

    self.assertEqual(
        stored["scene_types"]["pod_date"]["context_override"],
        "Treat pod scenes as fragile first-impression territory.",
    )
    self.assertEqual(
        loaded["scene_types"]["pod_date"]["context_override"],
        "Treat pod scenes as fragile first-impression territory.",
    )

  def test_scene_type_memory_override_persists_through_draft_json(self):
    draft = config_io.make_default_draft()
    draft["scene_types"]["pod_date"]["memory_override"] = (
        "Use only the pod opener and the current tension beat."
    )
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))

    path = config_io.save_draft(draft, "scene_type_memory_override", paths)
    stored = config_io.load_json(path)
    loaded = config_io.load_draft("scene_type_memory_override", paths)

    self.assertEqual(
        stored["scene_types"]["pod_date"]["memory_override"],
        "Use only the pod opener and the current tension beat.",
    )
    self.assertEqual(
        loaded["scene_types"]["pod_date"]["memory_override"],
        "Use only the pod opener and the current tension beat.",
    )

  def test_scene_type_memory_filter_persists_through_draft_json(self):
    draft = config_io.make_default_draft()
    draft["scene_types"]["pod_date"]["memory_filter"] = (
        "pod date\nfirst impression"
    )
    paths = config_io.StarterPaths(Path(self.create_tempdir().full_path))

    path = config_io.save_draft(draft, "scene_type_memory_filter", paths)
    stored = config_io.load_json(path)
    loaded = config_io.load_draft("scene_type_memory_filter", paths)

    self.assertEqual(
        stored["scene_types"]["pod_date"]["memory_filter"],
        "pod date\nfirst impression",
    )
    self.assertEqual(
        loaded["scene_types"]["pod_date"]["memory_filter"],
        "pod date\nfirst impression",
    )

  def test_build_config_adds_local_scene_type_instructions_component(self):
    draft = config_io.make_default_draft()
    draft["scene_types"]["pod_date"]["instructions_override"] = (
        "Keep the scene emotionally restrained."
    )

    config = config_io.build_config(draft)

    gm_instances = [
        item
        for item in config.instances
        if item.role == prefab_lib.Role.GAME_MASTER
    ]
    replacement_components = gm_instances[0].params["replacement_components"]
    self.assertIsInstance(
        replacement_components["instructions"],
        scene_type_instructions.SceneTypeInstructionsOverride,
    )

  def test_build_config_adds_local_scene_type_examples_component(self):
    draft = config_io.make_default_draft()
    draft["scene_types"]["pod_date"]["examples_override"] = (
        "Exercise: Keep the banter light. --- Response: A playful beat lands."
    )

    config = config_io.build_config(draft)

    gm_instances = [
        item
        for item in config.instances
        if item.role == prefab_lib.Role.GAME_MASTER
    ]
    self.assertIsInstance(
        gm_instances[0].params["replacement_components"]["examples"],
        scene_type_instructions.SceneTypeExamplesOverride,
    )

  def test_build_config_with_scene_type_prompt_replacements_builds_gm(self):
    draft = config_io.make_default_draft()
    draft["scene_types"]["pod_date"]["instructions_override"] = (
        "Keep the scene emotionally restrained."
    )
    draft["scene_types"]["pod_date"]["examples_override"] = (
        "Exercise: Keep the banter light. --- Response: A playful beat lands."
    )

    config = config_io.build_config(draft)

    gm_instance = next(
        item
        for item in config.instances
        if item.role == prefab_lib.Role.GAME_MASTER
    )
    gm_prefab = copy.deepcopy(config.prefabs[gm_instance.prefab])
    gm_prefab.params = gm_instance.params
    gm_prefab.entities = [
        SimpleNamespace(name="Alex"),
        SimpleNamespace(name="Blair"),
    ]

    gm = gm_prefab.build(
        model=no_language_model.NoLanguageModel(),
        memory_bank=basic_associative_memory.AssociativeMemoryBank(
            sentence_embedder=_embedder
        ),
    )
    component_order = gm.get_act_component().get_context_concat_order()

    self.assertEqual(
        len(component_order),
        len(set(component_order)),
    )
    self.assertLess(
        component_order.index("instructions"),
        component_order.index("scene_type_examples"),
    )
    self.assertLess(
        component_order.index("scene_type_examples"),
        component_order.index("player_characters"),
    )

  def test_build_config_adds_local_scene_type_context_component(self):
    draft = config_io.make_default_draft()
    draft["scene_types"]["pod_date"]["context_override"] = (
        "Treat pod scenes as fragile first-impression territory."
    )

    config = config_io.build_config(draft)

    gm_instances = [
        item
        for item in config.instances
        if item.role == prefab_lib.Role.GAME_MASTER
    ]
    self.assertEqual(
        gm_instances[0].params["extra_components_index"]["scene_type_context"],
        3,
    )
    self.assertIsInstance(
        gm_instances[0].params["extra_components"]["scene_type_context"],
        scene_type_instructions.SceneTypeContextOverride,
    )

  def test_build_config_adds_local_scene_type_memory_component(self):
    draft = config_io.make_default_draft()
    draft["scene_types"]["pod_date"]["memory_filter"] = (
        "pod date\nfirst impression"
    )

    config = config_io.build_config(draft)

    gm_instances = [
        item
        for item in config.instances
        if item.role == prefab_lib.Role.GAME_MASTER
    ]
    self.assertEqual(
        gm_instances[0].params["extra_components_index"]["scene_type_memory"],
        4,
    )
    self.assertIsInstance(
        gm_instances[0].params["extra_components"]["scene_type_memory"],
        scene_type_instructions.SceneTypeMemoryOverrideOrFilter,
    )

  def test_build_config_skips_local_scene_type_instructions_component_when_blank(
      self,
  ):
    draft = config_io.make_default_draft()
    draft["scene_types"]["pod_date"]["instructions_override"] = "   "

    config = config_io.build_config(draft)

    gm_instances = [
        item
        for item in config.instances
        if item.role == prefab_lib.Role.GAME_MASTER
    ]
    self.assertNotIn("extra_components", gm_instances[0].params)

  def test_build_config_skips_local_scene_type_examples_component_when_blank(
      self,
  ):
    draft = config_io.make_default_draft()
    draft["scene_types"]["pod_date"]["examples_override"] = "   "

    config = config_io.build_config(draft)

    gm_instances = [
        item
        for item in config.instances
        if item.role == prefab_lib.Role.GAME_MASTER
    ]
    self.assertNotIn("extra_components", gm_instances[0].params)

  def test_build_config_skips_local_scene_type_context_component_when_blank(self):
    draft = config_io.make_default_draft()
    draft["scene_types"]["pod_date"]["context_override"] = "   "

    config = config_io.build_config(draft)

    gm_instances = [
        item
        for item in config.instances
        if item.role == prefab_lib.Role.GAME_MASTER
    ]
    self.assertNotIn("extra_components", gm_instances[0].params)

  def test_build_config_skips_local_scene_type_memory_component_when_blank(self):
    draft = config_io.make_default_draft()
    draft["scene_types"]["pod_date"]["memory_override"] = "   "
    draft["scene_types"]["pod_date"]["memory_filter"] = "   "

    config = config_io.build_config(draft)

    gm_instances = [
        item
        for item in config.instances
        if item.role == prefab_lib.Role.GAME_MASTER
    ]
    self.assertNotIn("extra_components", gm_instances[0].params)

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
