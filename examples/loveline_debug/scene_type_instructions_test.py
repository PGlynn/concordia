"""Tests for Loveline-local scene-type instruction overrides."""

from absl.testing import absltest

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

  def __init__(self, scene_type_name: str):
    self._tracker = _FakeSceneTracker(scene_type_name)

  def get_phase(self):
    return entity_component.Phase.PRE_ACT

  def get_component(self, name: str, *, type_=object):
    del type_
    if name != "next_game_master":
      raise LookupError(name)
    return self._tracker


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


if __name__ == "__main__":
  absltest.main()
