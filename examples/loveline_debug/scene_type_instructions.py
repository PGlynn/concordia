"""Local scene-type instruction override support for Loveline debug."""

from __future__ import annotations

from collections.abc import Mapping

from concordia.components.agent import action_spec_ignored
from concordia.components.game_master import instructions as instructions_component
from concordia.components.game_master import scene_tracker


class SceneTypeInstructionsOverride(action_spec_ignored.ActionSpecIgnored):
  """Uses stock GM instructions unless the active scene type has an override."""

  def __init__(
      self,
      overrides_by_scene_type: Mapping[str, str],
      scene_tracker_component_key: str = (
          scene_tracker.DEFAULT_SCENE_TRACKER_COMPONENT_KEY
      ),
      pre_act_label: str = (
          instructions_component.DEFAULT_INSTRUCTIONS_PRE_ACT_LABEL
      ),
  ):
    super().__init__(pre_act_label=pre_act_label)
    self._overrides_by_scene_type = {
        str(name): str(value)
        for name, value in overrides_by_scene_type.items()
        if str(value).strip()
    }
    self._scene_tracker_component_key = scene_tracker_component_key
    self._default_instructions = (
        instructions_component.Instructions(pre_act_label=pre_act_label)
        .get_state()["state"]
    )

  def _make_pre_act_value(self) -> str:
    scene_type_name = None
    try:
      tracker = self.get_entity().get_component(
          self._scene_tracker_component_key,
          type_=scene_tracker.SceneTracker,
      )
      scene_type_name = tracker.get_current_scene_type().name
    except (LookupError, RuntimeError, IndexError, AttributeError):
      scene_type_name = None
    override = self._overrides_by_scene_type.get(scene_type_name or "")
    value = override or self._default_instructions
    self._logging_channel({
        "Key": self.get_pre_act_label(),
        "Value": value,
        "Scene type": scene_type_name,
    })
    return value


def scene_type_instruction_overrides(
    scene_types: Mapping[str, Mapping[str, str]],
) -> dict[str, str]:
  return {
      scene_type_name: str(cfg.get("instructions_override", ""))
      for scene_type_name, cfg in scene_types.items()
      if str(cfg.get("instructions_override", "")).strip()
  }
