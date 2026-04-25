"""Debug-local stock basic entity prefab with constrained component toggles."""

from __future__ import annotations

import dataclasses
from typing import Any, Mapping

from concordia.agents import entity_agent_with_logging
from concordia.associative_memory import basic_associative_memory
from concordia.components import agent as agent_components
from concordia.language_model import language_model
from concordia.typing import prefab as prefab_lib


STOCK_BASIC_ENTITY_COMPONENT_DEFAULTS = {
    "SituationPerception": True,
    "SelfPerception": True,
    "PersonBySituation": True,
}

_DEFAULT_OBSERVATION_HISTORY_LENGTH = 1_000_000
_DEFAULT_SITUATION_PERCEPTION_HISTORY_LENGTH = 25
_DEFAULT_SELF_PERCEPTION_HISTORY_LENGTH = 1_000_000
_DEFAULT_PERSON_BY_SITUATION_HISTORY_LENGTH = 5


def _spoken_dialogue_instructions(agent_name: str) -> str:
  return (
      f"The instructions for how to play the role of {agent_name} are as "
      "follows. This is a social science experiment studying how well you "
      f"play the role of a character named {agent_name}. The experiment "
      "is structured as a tabletop roleplaying game (like dungeons and "
      "dragons). However, in this case it is a serious social science "
      "experiment and simulation. The goal is to be realistic. It is "
      f"important to play the role of a person like {agent_name} as "
      f"accurately as possible, i.e., by responding in ways that you think "
      f"it is likely a person like {agent_name} would respond, and taking "
      f"into account all information about {agent_name} that you have. "
      "For free-action dialogue, respond only with the exact spoken words "
      "the character says in first person. Do not narrate actions, describe "
      "facial expressions, include stage directions, include non-verbal "
      "sounds, or prefix the line with the character name."
  )


def _component_toggles(params: Mapping[str, Any]) -> dict[str, bool]:
  raw = params.get("stock_basic_entity_components", {})
  if not isinstance(raw, Mapping):
    raw = {}
  return {
      name: bool(raw.get(name, default))
      for name, default in STOCK_BASIC_ENTITY_COMPONENT_DEFAULTS.items()
  }


@dataclasses.dataclass
class Entity(prefab_lib.Prefab):
  """A Loveline debug wrapper around stock basic__Entity component assembly."""

  description: str = (
      "A debug-local basic entity that can disable the three generated "
      "question components exposed by stock basic__Entity."
  )
  params: Mapping[str, Any] = dataclasses.field(
      default_factory=lambda: {
          "name": "Alice",
          "goal": "",
          "randomize_choices": True,
          "prefix_entity_name": False,
          "observation_history_length": _DEFAULT_OBSERVATION_HISTORY_LENGTH,
          "situation_perception_history_length": (
              _DEFAULT_SITUATION_PERCEPTION_HISTORY_LENGTH
          ),
          "self_perception_history_length": (
              _DEFAULT_SELF_PERCEPTION_HISTORY_LENGTH
          ),
          "person_by_situation_history_length": (
              _DEFAULT_PERSON_BY_SITUATION_HISTORY_LENGTH
          ),
          "stock_basic_entity_components": (
              STOCK_BASIC_ENTITY_COMPONENT_DEFAULTS.copy()
          ),
      }
  )

  def build(
      self,
      model: language_model.LanguageModel,
      memory_bank: basic_associative_memory.AssociativeMemoryBank,
  ) -> entity_agent_with_logging.EntityAgentWithLogging:
    entity_name = self.params.get("name", "Alice")
    entity_goal = self.params.get("goal", "")
    randomize_choices = self.params.get("randomize_choices", True)
    prefix_entity_name = self.params.get("prefix_entity_name", False)
    observation_history_length = self.params.get(
        "observation_history_length", _DEFAULT_OBSERVATION_HISTORY_LENGTH
    )
    situation_perception_history_length = self.params.get(
        "situation_perception_history_length",
        _DEFAULT_SITUATION_PERCEPTION_HISTORY_LENGTH,
    )
    self_perception_history_length = self.params.get(
        "self_perception_history_length",
        _DEFAULT_SELF_PERCEPTION_HISTORY_LENGTH,
    )
    person_by_situation_history_length = self.params.get(
        "person_by_situation_history_length",
        _DEFAULT_PERSON_BY_SITUATION_HISTORY_LENGTH,
    )
    enabled = _component_toggles(self.params)

    memory_key = agent_components.memory.DEFAULT_MEMORY_COMPONENT_KEY
    memory = agent_components.memory.AssociativeMemory(memory_bank=memory_bank)

    instructions_key = "Instructions"
    instructions = agent_components.constant.Constant(
        state=_spoken_dialogue_instructions(entity_name),
        pre_act_label="\nInstructions",
    )

    observation_to_memory_key = "Observation"
    observation_to_memory = agent_components.observation.ObservationToMemory()

    observation_key = (
        agent_components.observation.DEFAULT_OBSERVATION_COMPONENT_KEY
    )
    observation = agent_components.observation.LastNObservations(
        history_length=observation_history_length,
        pre_act_label=(
            "\nEvents so far (ordered from least recent to most recent)"
        ),
    )

    components_of_agent = {
        instructions_key: instructions,
        observation_to_memory_key: observation_to_memory,
        observation_key: observation,
        memory_key: memory,
    }

    situation_perception_key = "SituationPerception"
    if enabled[situation_perception_key]:
      situation_perception = (
          agent_components.question_of_recent_memories.SituationPerception(
              model=model,
              num_memories_to_retrieve=situation_perception_history_length,
              pre_act_label=(
                  f"\nQuestion: What situation is {entity_name} in right now?"
                  "\nAnswer"
              ),
          )
      )
      components_of_agent[situation_perception_key] = situation_perception

    self_perception_key = "SelfPerception"
    if enabled[self_perception_key]:
      dependencies = []
      if enabled[situation_perception_key]:
        dependencies.append(situation_perception_key)
      self_perception = (
          agent_components.question_of_recent_memories.SelfPerception(
              model=model,
              num_memories_to_retrieve=self_perception_history_length,
              components=dependencies,
              pre_act_label=(
                  f"\nQuestion: What kind of person is {entity_name}?\nAnswer"
              ),
          )
      )
      components_of_agent[self_perception_key] = self_perception

    person_by_situation_key = "PersonBySituation"
    if enabled[person_by_situation_key]:
      dependencies = [
          key
          for key in (self_perception_key, situation_perception_key)
          if enabled[key]
      ]
      person_by_situation = (
          agent_components.question_of_recent_memories.PersonBySituation(
              model=model,
              num_memories_to_retrieve=person_by_situation_history_length,
              components=dependencies,
              pre_act_label=(
                  f"\nQuestion: What would a person like {entity_name} do in "
                  "a situation like this?\nAnswer"
              ),
          )
      )
      components_of_agent[person_by_situation_key] = person_by_situation

    component_order = [
        key
        for key in (
            instructions_key,
            observation_to_memory_key,
            self_perception_key,
            situation_perception_key,
            person_by_situation_key,
            observation_key,
            memory_key,
        )
        if key in components_of_agent
    ]

    if entity_goal:
      goal_key = "Goal"
      overarching_goal = agent_components.constant.Constant(
          state=entity_goal, pre_act_label="\nGoal"
      )
      components_of_agent[goal_key] = overarching_goal
      component_order.insert(1, goal_key)

    act_component = agent_components.concat_act_component.ConcatActComponent(
        model=model,
        component_order=component_order,
        randomize_choices=randomize_choices,
        prefix_entity_name=prefix_entity_name,
    )

    return entity_agent_with_logging.EntityAgentWithLogging(
        agent_name=entity_name,
        act_component=act_component,
        context_components=components_of_agent,
        measurements=self.params.get("measurements"),
    )
