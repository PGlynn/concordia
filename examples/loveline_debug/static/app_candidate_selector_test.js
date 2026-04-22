const assert = require("assert/strict");

const {
  applyCandidateFormBlocks,
  candidateEditorHtml,
  candidateSelectorHtml,
} = require("./app.js");

function fieldMap(values) {
  return new Map(Object.entries(values).map(([key, value]) => {
    const control = typeof value === "boolean" ? {checked: value, value: ""} : {value};
    return [`[data-candidate-field="${key}"]`, control];
  }));
}

function testSelectorMarksOnlyChosenCandidateSelected() {
  const html = candidateSelectorHtml([
    {name: "Alex"},
    {name: "Blake"},
    {name: "Casey"},
  ], 1);

  assert.match(html, /<select id="candidateSelect">/);
  assert.match(html, /<option value="0">Alex<\/option>/);
  assert.match(html, /<option value="1" selected>Blake<\/option>/);
  assert.match(html, /<option value="2">Casey<\/option>/);
}

function testCandidateEditorRendersOneCandidateBlock() {
  const html = candidateEditorHtml({
    id: "blake_id",
    name: "Blake",
    gender: "woman",
    prefab: "basic__Entity",
    entity_params: {goal: "Win the room"},
  }, 1);

  assert.match(html, /data-candidate-index="1"/);
  assert.match(html, /value="Blake"/);
  assert.match(html, /<select data-candidate-field="prefab">/);
  assert.match(html, /<option value="basic__Entity" selected>basic Entity<\/option>/);
  assert.doesNotMatch(html, /Alex/);
}

function testRenderedCandidateCollectionPreservesHiddenContestants() {
  const contestants = [
    {
      id: "alex_id",
      name: "Alex",
      gender: "man",
      entity_params: {name: "Alex", goal: "Hidden goal"},
    },
    {
      id: "blake_id",
      name: "Blake",
      gender: "woman",
      prefab: "basic__Entity",
      entity_params: {
        name: "Blake",
        goal: "Old visible goal",
        prefix_entity_name: false,
      },
      player_specific_context: "Old context",
      player_specific_memories: ["old memory"],
      derived_debug_tags: ["woman"],
    },
  ];
  const fields = fieldMap({
    id: "blake_id",
    name: "Edited Blake",
    gender: "woman",
    prefab: "custom__Entity",
    goal: "Edited visible goal",
    prefix_entity_name: true,
    SituationPerception: true,
    SelfPerception: false,
    PersonBySituation: true,
    observation_history_length: "5",
    situation_perception_history_length: "",
    self_perception_history_length: "",
    person_by_situation_history_length: "",
    player_specific_context: "Edited context",
    player_specific_memories: "memory one\nmemory two",
    derived_debug_tags: "woman\nedited",
  });
  const block = {
    dataset: {candidateIndex: "1"},
    querySelector: (selector) => fields.get(selector),
  };

  const next = applyCandidateFormBlocks(contestants, [block], (index) => contestants[index]);

  assert.equal(next.length, 2);
  assert.deepEqual(next[0], contestants[0]);
  assert.equal(next[1].name, "Edited Blake");
  assert.equal(next[1].entity_params.goal, "Edited visible goal");
  assert.equal(next[1].entity_params.prefix_entity_name, true);
  assert.equal(next[1].entity_params.observation_history_length, 5);
  assert.deepEqual(next[1].player_specific_memories, ["memory one", "memory two"]);
  assert.deepEqual(next[1].derived_debug_tags, ["woman", "edited"]);
}

testSelectorMarksOnlyChosenCandidateSelected();
testCandidateEditorRendersOneCandidateBlock();
testRenderedCandidateCollectionPreservesHiddenContestants();
console.log("app_candidate_selector_test passed");
