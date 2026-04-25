"""Loveline-local formative memories initializer prefab."""

from collections.abc import Mapping, Sequence
import dataclasses
from typing import Any

from concordia.agents import entity_agent_with_logging
from concordia.associative_memory import basic_associative_memory
from concordia.components import game_master as gm_components
from concordia.language_model import language_model
from concordia.prefabs.game_master import (
    formative_memories_initializer as stock_initializer,
)
from concordia.typing import prefab as prefab_lib


@dataclasses.dataclass
class GameMaster(prefab_lib.Prefab):
  """Loveline-local initializer that forwards skip settings to the component."""

  description: str = stock_initializer.GameMaster.description
  params: Mapping[str, Any] = dataclasses.field(
      default_factory=lambda: {
          "name": "initial setup rules",
          "next_game_master_name": "default rules",
          "shared_memories": [],
          "player_specific_context": {},
          "player_specific_memories": {},
          "skip_formative_memories_for": [],
      }
  )
  entities: Sequence[entity_agent_with_logging.EntityAgentWithLogging] = ()

  def build(
      self,
      model: language_model.LanguageModel,
      memory_bank: basic_associative_memory.AssociativeMemoryBank,
  ) -> entity_agent_with_logging.EntityAgentWithLogging:
    name = self.params.get("name", "initial setup rules")
    next_game_master_name = self.params.get(
        "next_game_master_name", "default rules"
    )
    player_names = [entity.name for entity in self.entities]
    components = stock_initializer.build_components(
        model=model,
        memory_bank=memory_bank,
        player_names=player_names,
        next_game_master_name=next_game_master_name,
        shared_memories=self.params.get("shared_memories", []),
        player_specific_memories=self.params.get(
            "player_specific_memories", {}
        ),
        player_specific_context=self.params.get("player_specific_context", {}),
    )
    components[
        gm_components.next_game_master.DEFAULT_NEXT_GAME_MASTER_COMPONENT_KEY
    ] = gm_components.formative_memories_initializer.FormativeMemoriesInitializer(
        model=model,
        next_game_master_name=next_game_master_name,
        player_names=player_names,
        shared_memories=self.params.get("shared_memories", []),
        player_specific_memories=self.params.get(
            "player_specific_memories", {}
        ),
        player_specific_context=self.params.get("player_specific_context", {}),
        skip_formative_memories_for=self.params.get(
            "skip_formative_memories_for", []
        ),
    )
    return stock_initializer.build_game_master(
        model=model,
        name=name,
        player_names=player_names,
        components=components,
        measurements=self.params.get("measurements"),
    )
