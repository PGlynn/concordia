"""Local scene-type prompt component overrides for Loveline debug."""

from __future__ import annotations

from collections.abc import Mapping
from typing import override

from concordia.components.agent import action_spec_ignored
from concordia.components.agent import memory as memory_component
from concordia.components.game_master import instructions as instructions_component
from concordia.components.game_master import scene_tracker
from concordia.typing import entity as entity_lib


def _active_scene_type_name(
    component: action_spec_ignored.ActionSpecIgnored,
    scene_tracker_component_key: str,
) -> str | None:
  try:
    tracker = component.get_entity().get_component(
        scene_tracker_component_key,
        type_=scene_tracker.SceneTracker,
    )
    return tracker.get_current_scene_type().name
  except (LookupError, RuntimeError, IndexError, AttributeError):
    return None


class _OptionalSceneTypeComponent(action_spec_ignored.ActionSpecIgnored):
  """Omits itself from pre-act output when there is no active scene-type value."""

  @override
  def pre_act(
      self,
      action_spec: entity_lib.ActionSpec,
  ) -> str:
    del action_spec
    value = self.get_pre_act_value()
    if not value:
      return ""
    return f"{self.get_pre_act_label()}:\n{value}\n"


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
    scene_type_name = _active_scene_type_name(
        self, self._scene_tracker_component_key
    )
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


class SceneTypeExamplesOverride(action_spec_ignored.ActionSpecIgnored):
  """Uses stock workflow examples unless the active scene type overrides them."""

  def __init__(
      self,
      overrides_by_scene_type: Mapping[str, str],
      scene_tracker_component_key: str = (
          scene_tracker.DEFAULT_SCENE_TRACKER_COMPONENT_KEY
      ),
      pre_act_label: str = "Game master workflow examples",
  ):
    super().__init__(pre_act_label=pre_act_label)
    self._overrides_by_scene_type = {
        str(name): str(value)
        for name, value in overrides_by_scene_type.items()
        if str(value).strip()
    }
    self._scene_tracker_component_key = scene_tracker_component_key
    self._default_examples = (
        instructions_component.ExamplesSynchronous(pre_act_label=pre_act_label)
        .get_state()["state"]
    )

  def _make_pre_act_value(self) -> str:
    scene_type_name = _active_scene_type_name(
        self, self._scene_tracker_component_key
    )
    override = self._overrides_by_scene_type.get(scene_type_name or "")
    value = override or self._default_examples
    self._logging_channel({
        "Key": self.get_pre_act_label(),
        "Value": value,
        "Scene type": scene_type_name,
    })
    return value


def scene_type_examples_overrides(
    scene_types: Mapping[str, Mapping[str, str]],
) -> dict[str, str]:
  return {
      scene_type_name: str(cfg.get("examples_override", ""))
      for scene_type_name, cfg in scene_types.items()
      if str(cfg.get("examples_override", "")).strip()
  }


class SceneTypeContextOverride(_OptionalSceneTypeComponent):
  """Adds optional scene-type-local context to the GM prompt."""

  def __init__(
      self,
      overrides_by_scene_type: Mapping[str, str],
      scene_tracker_component_key: str = (
          scene_tracker.DEFAULT_SCENE_TRACKER_COMPONENT_KEY
      ),
      pre_act_label: str = "Scene-type context override",
  ):
    super().__init__(pre_act_label=pre_act_label)
    self._overrides_by_scene_type = {
        str(name): str(value)
        for name, value in overrides_by_scene_type.items()
        if str(value).strip()
    }
    self._scene_tracker_component_key = scene_tracker_component_key

  def _make_pre_act_value(self) -> str:
    scene_type_name = _active_scene_type_name(
        self, self._scene_tracker_component_key
    )
    value = self._overrides_by_scene_type.get(scene_type_name or "", "")
    self._logging_channel({
        "Key": self.get_pre_act_label(),
        "Value": value,
        "Scene type": scene_type_name,
    })
    return value


def scene_type_context_overrides(
    scene_types: Mapping[str, Mapping[str, str]],
) -> dict[str, str]:
  return {
      scene_type_name: str(cfg.get("context_override", ""))
      for scene_type_name, cfg in scene_types.items()
      if str(cfg.get("context_override", "")).strip()
  }


class SceneTypeMemoryOverrideOrFilter(_OptionalSceneTypeComponent):
  """Adds optional scene-type memory text or filtered recent memories."""

  def __init__(
      self,
      overrides_by_scene_type: Mapping[str, str],
      filters_by_scene_type: Mapping[str, str],
      scene_tracker_component_key: str = (
          scene_tracker.DEFAULT_SCENE_TRACKER_COMPONENT_KEY
      ),
      memory_component_key: str = (
          memory_component.DEFAULT_MEMORY_COMPONENT_KEY
      ),
      pre_act_label: str = "Scene-type memory override or filter",
      max_memories: int = 25,
  ):
    super().__init__(pre_act_label=pre_act_label)
    self._overrides_by_scene_type = {
        str(name): str(value)
        for name, value in overrides_by_scene_type.items()
        if str(value).strip()
    }
    self._filters_by_scene_type = {
        str(name): str(value)
        for name, value in filters_by_scene_type.items()
        if str(value).strip()
    }
    self._scene_tracker_component_key = scene_tracker_component_key
    self._memory_component_key = memory_component_key
    self._max_memories = max_memories

  def _make_pre_act_value(self) -> str:
    scene_type_name = _active_scene_type_name(
        self, self._scene_tracker_component_key
    )
    override = self._overrides_by_scene_type.get(scene_type_name or "", "")
    if override:
      self._logging_channel({
          "Key": self.get_pre_act_label(),
          "Value": override,
          "Scene type": scene_type_name,
          "Mode": "override",
      })
      return override

    filter_text = self._filters_by_scene_type.get(scene_type_name or "", "")
    if not filter_text:
      self._logging_channel({
          "Key": self.get_pre_act_label(),
          "Value": "",
          "Scene type": scene_type_name,
          "Mode": "inactive",
      })
      return ""

    filters = [
        line.strip().lower()
        for line in filter_text.splitlines()
        if line.strip()
    ]
    memory = self.get_entity().get_component(
        self._memory_component_key,
        type_=memory_component.Memory,
    )
    matches = [
        item
        for item in memory.retrieve_recent(limit=self._max_memories)
        if any(token in item.lower() for token in filters)
    ]
    value = (
        "\n".join(matches)
        if matches
        else "No recent memories matched the active scene-type filter."
    )
    self._logging_channel({
        "Key": self.get_pre_act_label(),
        "Value": value,
        "Scene type": scene_type_name,
        "Mode": "filter",
        "Filter": filter_text,
    })
    return value


def scene_type_memory_overrides(
    scene_types: Mapping[str, Mapping[str, str]],
) -> dict[str, str]:
  return {
      scene_type_name: str(cfg.get("memory_override", ""))
      for scene_type_name, cfg in scene_types.items()
      if str(cfg.get("memory_override", "")).strip()
  }


def scene_type_memory_filters(
    scene_types: Mapping[str, Mapping[str, str]],
) -> dict[str, str]:
  return {
      scene_type_name: str(cfg.get("memory_filter", ""))
      for scene_type_name, cfg in scene_types.items()
      if str(cfg.get("memory_filter", "")).strip()
  }
