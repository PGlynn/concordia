const assert = require("assert/strict");

const {
  BASIC_ENTITY_HISTORY_LENGTH_FIELDS,
  collectHistoryLengthParams,
  historyLengthFieldsHtml,
  mergeSelectionDraft,
} = require("./app.js");

function testHistoryLengthFieldsRenderExistingValues() {
  const html = historyLengthFieldsHtml({
    observation_history_length: 7,
    situation_perception_history_length: 8,
    self_perception_history_length: 9,
    person_by_situation_history_length: 10,
  });

  for (const [key] of BASIC_ENTITY_HISTORY_LENGTH_FIELDS) {
    assert.match(html, new RegExp(`data-candidate-field="${key}"`));
  }
  assert.match(html, /value="7"/);
  assert.match(html, /value="10"/);
}

function testCollectHistoryLengthParamsUsesEnteredNumbers() {
  const values = new Map([
    ["observation_history_length", "11"],
    ["situation_perception_history_length", "12"],
    ["self_perception_history_length", "13"],
    ["person_by_situation_history_length", "14"],
  ]);
  const params = collectHistoryLengthParams((key) => ({value: values.get(key)}));

  assert.deepEqual(params, {
    observation_history_length: 11,
    situation_perception_history_length: 12,
    self_perception_history_length: 13,
    person_by_situation_history_length: 14,
  });
}

function testCollectHistoryLengthParamsKeepsRawValueWhenBlank() {
  const params = collectHistoryLengthParams(
    () => ({value: ""}),
    {observation_history_length: 23}
  );

  assert.deepEqual(params, {observation_history_length: 23});
}

function testSelectionMergePreservesEditedHistoryLengthsByCandidateId() {
  const currentDraft = {
    selected_candidate_ids: ["male_a", "female_a"],
    contestants: [
      {
        id: "male_a",
        name: "Edited Alex",
        gender: "man",
        entity_params: {
          name: "Edited Alex",
          observation_history_length: 3,
          situation_perception_history_length: 4,
          self_perception_history_length: 5,
          person_by_situation_history_length: 6,
        },
      },
    ],
    scenes: [],
  };
  const selectionDraft = {
    selected_candidate_ids: ["male_a", "female_b"],
    contestants: [
      {
        id: "male_a",
        name: "Stock Alex",
        gender: "man",
        entity_params: {
          name: "Stock Alex",
          observation_history_length: 1000000,
        },
      },
      {
        id: "female_b",
        name: "Stock Blake",
        gender: "woman",
        entity_params: {
          name: "Stock Blake",
          situation_perception_history_length: 25,
        },
      },
    ],
    scenes: [],
  };

  const merged = mergeSelectionDraft(currentDraft, selectionDraft);

  assert.equal(merged.contestants[0].entity_params.observation_history_length, 3);
  assert.equal(merged.contestants[0].entity_params.person_by_situation_history_length, 6);
  assert.equal(merged.contestants[1].entity_params.situation_perception_history_length, 25);
}

testHistoryLengthFieldsRenderExistingValues();
testCollectHistoryLengthParamsUsesEnteredNumbers();
testCollectHistoryLengthParamsKeepsRawValueWhenBlank();
testSelectionMergePreservesEditedHistoryLengthsByCandidateId();
console.log("app_candidate_history_test passed");
