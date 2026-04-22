const assert = require("assert/strict");

const {mergeSelectionDraft} = require("./app.js");

function testApplyPairPreservesUnsavedDraftEdits() {
  const currentDraft = {
    schema_version: 1,
    name: "unsaved_work",
    created_at: "created-before",
    updated_at: "updated-before",
    source_root: "/tmp/current-root",
    selected_candidate_ids: ["male_a", "female_a"],
    run: {
      max_steps: 42,
      disable_language_model: false,
      api_type: "ollama",
      model_name: "unsaved-model",
      checkpoint_every_step: false,
    },
    scene_defaults: {
      main_game_master_name: "Unsaved GM",
      default_premise: "Unsaved default premise",
    },
    scene_types: {
      custom_type: {
        rounds: 7,
        call_to_action: "Unsaved call to action",
      },
    },
    contestants: [
      {
        id: "male_a",
        name: "Edited Alex",
        gender: "man",
        prefab: "custom__Entity",
        entity_params: {
          name: "Edited Alex",
          goal: "Unsaved male goal",
          prefix_entity_name: true,
        },
        player_specific_context: "Unsaved male context",
        player_specific_memories: ["Unsaved male memory"],
        derived_debug_tags: ["man"],
      },
      {
        id: "female_a",
        name: "Edited Blake",
        gender: "woman",
        prefab: "basic__Entity",
        entity_params: {
          name: "Edited Blake",
          goal: "Old female goal",
          prefix_entity_name: false,
        },
        player_specific_context: "Old female context",
        player_specific_memories: ["Old female memory"],
        derived_debug_tags: ["woman"],
      },
    ],
    scenes: [
      {
        id: "unsaved_scene",
        type: "custom_type",
        num_rounds: 3,
        participants: ["Edited Alex", "Edited Blake"],
        premise: {
          "Edited Alex": ["Keep this male premise"],
          "Edited Blake": ["Keep this female premise"],
        },
      },
    ],
  };
  const selectionDraft = {
    schema_version: 1,
    name: "two_candidate_debug",
    created_at: "created-from-selection",
    updated_at: "updated-from-selection",
    source_root: "/tmp/selection-root",
    selected_candidate_ids: ["male_a", "female_b"],
    run: {
      max_steps: 8,
      disable_language_model: true,
      api_type: "ollama",
      model_name: "qwen3.5:35b-a3b",
      checkpoint_every_step: true,
    },
    scene_defaults: {
      main_game_master_name: "Show Runner",
      default_premise: "Generated default premise",
    },
    scene_types: {
      generated_type: {
        rounds: 1,
        call_to_action: "Generated call to action",
      },
    },
    contestants: [
      {
        id: "male_a",
        name: "Stock Alex",
        gender: "man",
        prefab: "basic__Entity",
        entity_params: {
          name: "Stock Alex",
          goal: "Stock male goal",
          prefix_entity_name: false,
        },
        player_specific_context: "Stock male context",
        player_specific_memories: ["Stock male memory"],
        derived_debug_tags: ["man"],
      },
      {
        id: "female_b",
        name: "Stock Casey",
        gender: "woman",
        prefab: "basic__Entity",
        entity_params: {
          name: "Stock Casey",
          goal: "Stock female goal",
          prefix_entity_name: false,
        },
        player_specific_context: "Stock female context",
        player_specific_memories: ["Stock female memory"],
        derived_debug_tags: ["woman"],
      },
    ],
    scenes: [
      {
        id: "generated_scene",
        type: "generated_type",
        participants: ["Stock Alex", "Stock Casey"],
        premise: {
          "Stock Alex": ["Generated male premise"],
          "Stock Casey": ["Generated female premise"],
        },
      },
    ],
  };

  const merged = mergeSelectionDraft(currentDraft, selectionDraft);

  assert.deepEqual(merged.selected_candidate_ids, ["male_a", "female_b"]);
  assert.equal(merged.name, "unsaved_work");
  assert.deepEqual(merged.run, currentDraft.run);
  assert.deepEqual(merged.scene_defaults, currentDraft.scene_defaults);
  assert.deepEqual(merged.scene_types, currentDraft.scene_types);

  assert.equal(merged.contestants[0].id, "male_a");
  assert.equal(merged.contestants[0].name, "Edited Alex");
  assert.equal(merged.contestants[0].prefab, "custom__Entity");
  assert.equal(merged.contestants[0].player_specific_context, "Unsaved male context");
  assert.equal(merged.contestants[1].id, "female_b");
  assert.equal(merged.contestants[1].name, "Stock Casey");
  assert.equal(merged.contestants[1].player_specific_context, "Stock female context");

  assert.equal(merged.scenes.length, 1);
  assert.equal(merged.scenes[0].id, "unsaved_scene");
  assert.equal(merged.scenes[0].type, "custom_type");
  assert.deepEqual(merged.scenes[0].participants, ["Edited Alex", "Stock Casey"]);
  assert.deepEqual(merged.scenes[0].premise, {
    "Edited Alex": ["Keep this male premise"],
    "Stock Casey": ["Keep this female premise"],
  });
}

testApplyPairPreservesUnsavedDraftEdits();
console.log("app_merge_selection_test passed");
