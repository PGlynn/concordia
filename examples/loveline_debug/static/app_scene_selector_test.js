const assert = require("assert/strict");

const {
  applySceneFormBlocks,
  sceneEditorHtml,
  sceneSelectorHtml,
  sceneTypeSelectorHtml,
} = require("./app.js");

function sceneBlock(index, values) {
  const fields = new Map([
    ['[data-scene-field="id"]', {value: values.id}],
    ['[data-scene-field="type"]', {value: values.type}],
    ['[data-scene-field="num_rounds"]', {value: values.num_rounds || ""}],
  ]);
  const participants = (values.participants || []).map((name) => ({
    dataset: {sceneParticipant: name},
  }));
  const premises = Object.entries(values.premise || {}).map(([name, text]) => ({
    dataset: {scenePremise: name},
    value: text,
  }));
  return {
    dataset: {sceneIndex: String(index)},
    querySelector: (selector) => fields.get(selector),
    querySelectorAll: (selector) => {
      if (selector === "[data-scene-participant]:checked") return participants;
      if (selector === "[data-scene-premise]") return premises;
      return [];
    },
  };
}

function testSelectorMarksOnlyChosenSceneSelected() {
  const html = sceneSelectorHtml([
    {id: "pod_intro"},
    {id: "pod_followup"},
    {id: "proposal"},
  ], 1);

  assert.match(html, /<select id="sceneSelect">/);
  assert.match(html, /<option value="0">pod_intro<\/option>/);
  assert.match(html, /<option value="1" selected>pod_followup<\/option>/);
  assert.match(html, /<option value="2">proposal<\/option>/);
}

function testSceneEditorRendersOneSceneBlock() {
  const html = sceneEditorHtml(
    {
      id: "pod_followup",
      type: "pod_date",
      participants: ["Alex"],
      premise: {Alex: ["Ask a careful question."]},
    },
    1,
    ["Alex", "Blake"],
  );

  assert.match(html, /data-scene-index="1"/);
  assert.match(html, /value="pod_followup"/);
  assert.match(html, /Ask a careful question/);
  assert.match(html, /scene\.participants/);
  assert.match(html, /type's default rounds/);
  assert.doesNotMatch(html, /pod_intro/);
}

function testSceneTypeSelectorRendersOneSelectedDefinition() {
  const html = sceneTypeSelectorHtml({
    pod_date: {rounds: 1},
    proposal: {rounds: 2},
  }, "proposal");

  assert.match(html, /<select id="sceneTypeSelect">/);
  assert.match(html, /<option value="pod_date">pod_date<\/option>/);
  assert.match(html, /<option value="proposal" selected>proposal<\/option>/);
}

function testRenderedSceneCollectionPreservesHiddenScenes() {
  const scenes = [
    {
      id: "pod_intro",
      type: "pod_date",
      participants: ["Alex", "Blake"],
      premise: {Alex: ["Hidden premise"]},
    },
    {
      id: "pod_followup",
      type: "pod_date",
      num_rounds: 2,
      participants: ["Alex"],
      premise: {Alex: ["Old visible premise"]},
    },
  ];

  const next = applySceneFormBlocks(
    scenes,
    [sceneBlock(1, {
      id: "edited_followup",
      type: "proposal",
      num_rounds: "3",
      participants: ["Blake"],
      premise: {Blake: "Edited premise\nSecond line"},
    })],
    (index) => scenes[index],
  );

  assert.equal(next.length, 2);
  assert.deepEqual(next[0], scenes[0]);
  assert.equal(next[1].id, "edited_followup");
  assert.equal(next[1].type, "proposal");
  assert.equal(next[1].num_rounds, 3);
  assert.deepEqual(next[1].participants, ["Blake"]);
  assert.deepEqual(next[1].premise.Blake, ["Edited premise", "Second line"]);
}

testSelectorMarksOnlyChosenSceneSelected();
testSceneEditorRendersOneSceneBlock();
testSceneTypeSelectorRendersOneSelectedDefinition();
testRenderedSceneCollectionPreservesHiddenScenes();
console.log("app_scene_selector_test passed");
