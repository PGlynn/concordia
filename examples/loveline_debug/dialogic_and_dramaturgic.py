"""Loveline-local dialogic GM wrapper with replaceable prompt components."""

from collections.abc import Mapping, Sequence
import dataclasses
from typing import Any

from concordia.agents import entity_agent_with_logging
from concordia.associative_memory import basic_associative_memory as associative_memory
from concordia.components import agent as actor_components
from concordia.components import game_master as gm_components
from concordia.components.game_master import event_resolution as thought_chains_lib
from concordia.language_model import language_model
from concordia.prefabs.game_master import dialogic_and_dramaturgic as stock_dialogic_and_dramaturgic
from concordia.typing import entity as entity_lib
from concordia.typing import prefab as prefab_lib
from concordia.typing import scene as scene_lib


DEFAULT_NAME = stock_dialogic_and_dramaturgic.DEFAULT_NAME
_INSTRUCTIONS_KEY = "instructions"
_EXAMPLES_KEY = "scene_type_examples"
_PLAYER_CHARACTERS_KEY = "player_characters"


@dataclasses.dataclass
class GameMaster(prefab_lib.Prefab):
  """Loveline-local GM that replaces stock prompt components when requested."""

  description: str = stock_dialogic_and_dramaturgic.GameMaster.description
  params: Mapping[str, Any] = dataclasses.field(
      default_factory=lambda: {
          "name": DEFAULT_NAME,
          "scenes": (),
          "replacement_components": {},
          "extra_components": {},
          "extra_components_index": {},
          "external_queue": None,
          "allow_llm_fallback": True,
      }
  )
  entities: Sequence[entity_lib.Entity] = dataclasses.field(default_factory=tuple)

  def build(
      self,
      model: language_model.LanguageModel,
      memory_bank: associative_memory.AssociativeMemoryBank,
  ) -> entity_lib.Entity:
    name = self.params.get("name", DEFAULT_NAME)
    replacement_components = self.params.get("replacement_components", {})
    extra_components = self.params.get("extra_components", {})
    extra_components_index = self.params.get("extra_components_index", {})

    if extra_components_index and extra_components:
      if extra_components_index.keys() != extra_components.keys():
        raise ValueError(
            "extra_components_index must have the same keys as"
            " extra_components."
        )

    player_names = [entity.name for entity in self.entities]
    external_queue = self.params.get("external_queue", None)

    scenes = self.params.get(
        "scenes",
        stock_dialogic_and_dramaturgic._configure_default_scenes(player_names),
    )
    assert isinstance(scenes, Sequence), "scenes must be a sequence."
    if scenes:
      assert isinstance(
          scenes[0], scene_lib.SceneSpec
      ), "scenes must be a sequence of SceneSpecs."

    instructions = replacement_components.get(
        "instructions", gm_components.instructions.Instructions()
    )

    player_characters = gm_components.instructions.PlayerCharacters(
        player_characters=player_names,
    )

    observation_to_memory_key = "observation_to_memory"
    observation_to_memory = actor_components.observation.ObservationToMemory()

    observation_component_key = (
        actor_components.observation.DEFAULT_OBSERVATION_COMPONENT_KEY
    )
    observation = actor_components.observation.LastNObservations(
        history_length=1000,
    )

    display_events_key = "display_events"
    display_events = gm_components.event_resolution.DisplayEvents(
        model=model,
        pre_act_label="Conversation",
    )

    memory_component_key = actor_components.memory.DEFAULT_MEMORY_COMPONENT_KEY
    memory = actor_components.memory.AssociativeMemory(memory_bank=memory_bank)

    make_observation_key = (
        gm_components.make_observation.DEFAULT_MAKE_OBSERVATION_COMPONENT_KEY
    )
    allow_llm_fallback = self.params.get("allow_llm_fallback", True)
    make_observation = gm_components.make_observation.MakeObservation(
        model=model,
        player_names=player_names,
        components=[
            observation_component_key,
            display_events_key,
        ],
        external_queue=external_queue,
        allow_llm_fallback=allow_llm_fallback,
    )

    scene_tracker = gm_components.scene_tracker.SceneTracker(
        model=model,
        scenes=scenes,
        observation_component_key=(
            gm_components.make_observation.DEFAULT_MAKE_OBSERVATION_COMPONENT_KEY
        ),
    )

    send_events_to_players_key = (
        gm_components.event_resolution.DEFAULT_SEND_PRE_ACT_VALUES_TO_PLAYERS_PRE_ACT_LABEL
    )
    scene_tracker_key = (
        gm_components.next_game_master.DEFAULT_NEXT_GAME_MASTER_COMPONENT_KEY
    )
    send_events_to_players = (
        gm_components.event_resolution.SendEventToRelevantPlayers(
            model=model,
            player_names=player_names,
            make_observation_component_key=make_observation_key,
            player_filter=scene_tracker.get_participants,
        )
    )

    next_actor_key = gm_components.next_acting.DEFAULT_NEXT_ACTING_COMPONENT_KEY
    next_action_spec_key = (
        gm_components.next_acting.DEFAULT_NEXT_ACTION_SPEC_COMPONENT_KEY
    )

    next_actor = gm_components.next_acting.NextActingFromSceneSpec(
        scene_tracker_component_key=scene_tracker_key,
    )
    next_action_spec = gm_components.next_acting.NextActionSpecFromSceneSpec(
        scene_tracker_component_key=scene_tracker_key,
    )

    identity_without_prefix = thought_chains_lib.RemoveSpecificText(
        substring_to_remove="Putative event to resolve:  "
    )

    event_resolution_key = (
        gm_components.switch_act.DEFAULT_RESOLUTION_COMPONENT_KEY
    )
    event_resolution = gm_components.event_resolution.EventResolution(
        model=model,
        event_resolution_steps=(identity_without_prefix,),
    )

    terminator_key = gm_components.terminate.DEFAULT_TERMINATE_COMPONENT_KEY
    terminator = gm_components.terminate.SceneBasedTerminator(
        scene_tracker_component_key=scene_tracker_key
    )

    components_of_game_master = {
        terminator_key: terminator,
        _INSTRUCTIONS_KEY: instructions,
        _PLAYER_CHARACTERS_KEY: player_characters,
        observation_component_key: observation,
        observation_to_memory_key: observation_to_memory,
        display_events_key: display_events,
        make_observation_key: make_observation,
        memory_component_key: memory,
        scene_tracker_key: scene_tracker,
        next_actor_key: next_actor,
        next_action_spec_key: next_action_spec,
        event_resolution_key: event_resolution,
    }
    if send_events_to_players is not None:
      components_of_game_master[send_events_to_players_key] = (
          send_events_to_players
      )

    component_order = list(components_of_game_master.keys())

    if "examples" in replacement_components:
      components_of_game_master[_EXAMPLES_KEY] = replacement_components["examples"]
      component_order.insert(
          component_order.index(_INSTRUCTIONS_KEY) + 1,
          _EXAMPLES_KEY,
      )

    if extra_components:
      components_of_game_master.update(extra_components)
      if extra_components_index:
        for component_name in extra_components.keys():
          component_order.insert(
              extra_components_index[component_name],
              component_name,
          )
      else:
        component_order = list(components_of_game_master.keys())

    act_component = gm_components.switch_act.SwitchAct(
        model=model,
        entity_names=player_names,
        component_order=component_order,
    )

    return entity_agent_with_logging.EntityAgentWithLogging(
        agent_name=name,
        act_component=act_component,
        context_components=components_of_game_master,
        measurements=self.params.get("measurements"),
    )
