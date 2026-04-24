"""Tests for Loveline-local scene-type instruction overrides."""

from absl.testing import absltest
from unittest import mock

from concordia.components.agent import memory as memory_component
from concordia.components.game_master import instructions as instructions_component
from concordia.typing import entity_component
from examples.loveline_debug import scene_type_instructions


class _FakeSceneType:

  def __init__(self, name: str):
    self.name = name


class _FakeSceneTracker:

  def __init__(self, scene_type_name: str):
    self._scene_type_name = scene_type_name

  def get_current_scene_type(self):
    return _FakeSceneType(self._scene_type_name)


class _FakeEntity:

  def __init__(self, scene_type_name: str, memories: tuple[str, ...] = ()):
    self._tracker = _FakeSceneTracker(scene_type_name)
    self._memory = _FakeMemory(memories)

  def get_phase(self):
    return entity_component.Phase.PRE_ACT

  def get_component(self, name: str, *, type_=object):
    del type_
    if name == "next_game_master":
      return self._tracker
    if name == memory_component.DEFAULT_MEMORY_COMPONENT_KEY:
      return self._memory
    raise LookupError(name)


class _FakeMemory(memory_component.Memory):

  def __init__(self, memories: tuple[str, ...]):
    self._memories = list(memories)

  def get_state(self):
    return {}

  def set_state(self, state):
    del state

  def retrieve_recent(self, limit: int = 1):
    return tuple(self._memories[-limit:])

  def scan(self, selector_fn):
    return tuple(item for item in self._memories if selector_fn(item))

  def add(self, text: str):
    self._memories.append(text)

  def extend(self, texts):
    self._memories.extend(texts)

  def update(self):
    return None

  def get_raw_memory(self):
    raise NotImplementedError()

  def get_all_memories_as_text(self):
    return tuple(self._memories)


class SceneTypeInstructionsTest(absltest.TestCase):

  def test_uses_override_for_active_scene_type(self):
    component = scene_type_instructions.SceneTypeInstructionsOverride({
        "pod_date": "Keep this scene breezy and a little teasing.",
    })
    component.set_entity(_FakeEntity("pod_date"))

    self.assertEqual(
        component.get_pre_act_value(),
        "Keep this scene breezy and a little teasing.",
    )

  def test_instructions_pre_act_runs_without_logging_channel_init(self):
    component = scene_type_instructions.SceneTypeInstructionsOverride({
        "pod_date": "Keep this scene breezy and a little teasing.",
    })
    component.set_entity(_FakeEntity("pod_date"))

    self.assertEqual(
        component.pre_act(None),
        "Instructions:\nKeep this scene breezy and a little teasing.\n",
    )

  def test_falls_back_to_stock_instructions_when_scene_type_has_no_override(self):
    component = scene_type_instructions.SceneTypeInstructionsOverride({
        "pod_date": "Keep this scene breezy and a little teasing.",
    })
    component.set_entity(_FakeEntity("confessional"))

    self.assertEqual(
        component.get_pre_act_value(),
        instructions_component.Instructions().get_state()["state"],
    )

  def test_uses_examples_override_for_active_scene_type(self):
    component = scene_type_instructions.SceneTypeExamplesOverride({
        "pod_date": "Exercise: Keep this scene punchy. --- Response: Warm banter.",
    })
    component.set_entity(_FakeEntity("pod_date"))

    self.assertEqual(
        component.get_pre_act_value(),
        "Exercise: Keep this scene punchy. --- Response: Warm banter.",
    )

  def test_examples_pre_act_runs_without_logging_channel_init(self):
    component = scene_type_instructions.SceneTypeExamplesOverride({
        "pod_date": "Exercise: Keep this scene punchy. --- Response: Warm"
                    " banter.",
    })
    component.set_entity(_FakeEntity("pod_date"))

    self.assertEqual(
        component.pre_act(None),
        "Game master workflow examples:\n"
        "Exercise: Keep this scene punchy. --- Response: Warm banter.\n",
    )

  def test_examples_fall_back_to_stock_examples_when_scene_type_has_no_override(
      self,
  ):
    component = scene_type_instructions.SceneTypeExamplesOverride({
        "pod_date": "Exercise: Keep this scene punchy. --- Response: Warm banter.",
    })
    component.set_entity(_FakeEntity("confessional"))

    self.assertEqual(
        component.get_pre_act_value(),
        component._default_examples,  # pylint: disable=protected-access
    )

  def test_uses_context_override_for_active_scene_type(self):
    component = scene_type_instructions.SceneTypeContextOverride({
        "pod_date": "Treat this as a delicate first-impression conversation.",
    })
    component.set_entity(_FakeEntity("pod_date"))

    self.assertEqual(
        component.get_pre_act_value(),
        "Treat this as a delicate first-impression conversation.",
    )

  def test_context_pre_act_runs_without_logging_channel_init(self):
    component = scene_type_instructions.SceneTypeContextOverride({
        "pod_date": "Treat this as a delicate first-impression conversation.",
    })
    component.set_entity(_FakeEntity("pod_date"))

    self.assertEqual(
        component.pre_act(None),
        "Scene-type context override:\n"
        "Treat this as a delicate first-impression conversation.\n",
    )

  def test_context_override_omits_pre_act_when_scene_type_has_no_value(self):
    component = scene_type_instructions.SceneTypeContextOverride({
        "pod_date": "Treat this as a delicate first-impression conversation.",
    })
    component.set_entity(_FakeEntity("confessional"))

    self.assertEqual(component.get_pre_act_value(), "")
    self.assertEqual(component.pre_act(None), "")

  def test_uses_memory_override_for_active_scene_type(self):
    component = scene_type_instructions.SceneTypeMemoryOverrideOrFilter(
        {"pod_date": "Use only the pod opener and current tension beat."},
        {},
    )
    component.set_entity(_FakeEntity("pod_date"))

    self.assertEqual(
        component.get_pre_act_value(),
        "Use only the pod opener and current tension beat.",
    )

  def test_memory_override_pre_act_runs_without_logging_channel_init(self):
    component = scene_type_instructions.SceneTypeMemoryOverrideOrFilter(
        {"pod_date": "Use only the pod opener and current tension beat."},
        {},
    )
    component.set_entity(_FakeEntity("pod_date"))

    self.assertEqual(
        component.pre_act(None),
        "Scene-type memory override or filter:\n"
        "Use only the pod opener and current tension beat.\n",
    )

  def test_filters_recent_memories_for_active_scene_type(self):
    component = scene_type_instructions.SceneTypeMemoryOverrideOrFilter(
        {},
        {"pod_date": "chemistry\nwall"},
        max_memories=5,
    )
    component.set_entity(
        _FakeEntity(
            "pod_date",
            memories=(
                "The pod wall keeps them unseen.",
                "Marcus is watching for chemistry.",
                "Confessional booths are empty.",
            ),
        )
    )

    self.assertEqual(
        component.get_pre_act_value(),
        "The pod wall keeps them unseen.\nMarcus is watching for chemistry.",
    )

  def test_scene_type_components_use_logging_channel_when_present(self):
    logger = mock.MagicMock()
    component = scene_type_instructions.SceneTypeExamplesOverride({
        "pod_date": "Exercise: Keep this scene punchy. --- Response: Warm banter.",
    })
    component.set_entity(_FakeEntity("pod_date"))
    component.set_logging_channel(logger)

    component.pre_act(None)

    logger.assert_called_once_with({
        "Key": "Game master workflow examples",
        "Value": "Exercise: Keep this scene punchy. --- Response: Warm banter.",
        "Scene type": "pod_date",
    })

  def test_memory_filter_omits_pre_act_when_scene_type_has_no_config(self):
    component = scene_type_instructions.SceneTypeMemoryOverrideOrFilter(
        {},
        {"pod_date": "chemistry"},
    )
    component.set_entity(_FakeEntity("confessional"))

    self.assertEqual(component.get_pre_act_value(), "")
    self.assertEqual(component.pre_act(None), "")


if __name__ == "__main__":
  absltest.main()
