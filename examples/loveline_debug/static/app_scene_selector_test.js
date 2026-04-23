const assert = require("assert/strict");

const {
  applySceneTypeFormBlock,
  applySceneFormBlocks,
  sceneEditorHtml,
  sceneTypeEditorHtml,
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

function sceneTypeBlock(values) {
  const fields = new Map([
    ['[data-scene-type-field="name"]', {value: values.name}],
    ['[data-scene-type-field="rounds"]', {value: values.rounds}],
    ['[data-scene-type-field="call_to_action"]', {value: values.call_to_action}],
    ['[data-scene-type-field="instructions_override"]', {value: values.instructions_override || ""}],
    ['[data-scene-type-field="examples_override"]', {value: values.examples_override || ""}],
    ['[data-scene-type-field="context_override"]', {value: values.context_override || ""}],
    ['[data-scene-type-field="memory_override"]', {value: values.memory_override || ""}],
    ['[data-scene-type-field="memory_filter"]', {value: values.memory_filter || ""}],
  ]);
  return {
    querySelector: (selector) => fields.get(selector),
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

function testSceneTypeEditorIncludesInstructionsOverrideField() {
  const html = sceneTypeEditorHtml("pod_date", {
    rounds: 1,
    call_to_action: "Say one short spoken reply.",
    instructions_override: "Keep the tone flirty but grounded.",
    examples_override: "Exercise: Narrate one flirt-forward beat. --- Warm, teasing response.",
    context_override: "Remember that this pod scene should feel tentative and intimate.",
    memory_override: "Use only the startup pod framing and the contestants' first impressions.",
    memory_filter: "pod date\nfirst impression",
  });

  assert.match(html, /Call to Action/);
  assert.match(html, /Instructions Override/);
  assert.match(html, /Few-Shot \/ Style Examples/);
  assert.match(html, /Scene Context Override/);
  assert.match(html, /Memory Override/);
  assert.match(html, /Memory Filter/);
  assert.match(
    html,
    /Optional local Loveline debug override\. Leave blank to use stock Concordia game master instructions\./,
  );
  assert.match(
    html,
    /Optional local Loveline debug workflow\/style examples\. Leave blank to use stock Concordia examples for this scene type\./,
  );
  assert.match(
    html,
    /Optional local Loveline debug scene-type context text\. Leave blank to omit extra scene-type context\./,
  );
  assert.match(
    html,
    /Optional local Loveline debug memory text for this scene type\. Takes priority over the memory filter when present\./,
  );
  assert.match(
    html,
    /Optional newline-separated case-insensitive match terms used to pull recent memories into a scene-type-local prompt block\./,
  );
  assert.match(html, /Keep the tone flirty but grounded\./);
  assert.match(html, /Exercise: Narrate one flirt-forward beat\./);
  assert.match(html, /tentative and intimate/);
  assert.match(html, /startup pod framing/);
  assert.match(html, /pod date/);
}

function testSceneTypeFormBlockPersistsInstructionsOverride() {
  const next = applySceneTypeFormBlock(
    {
      pod_date: {rounds: 2, call_to_action: "Old CTA"},
    },
    "pod_date",
    sceneTypeBlock({
      name: "pod_date",
      rounds: "3",
      call_to_action: "New CTA",
      instructions_override: "Keep it more playful.",
      examples_override: "Exercise: Say something witty. --- Witty response.",
      context_override: "Keep the scene focused on immediate chemistry.",
      memory_override: "Only remember the last pod beat and the current opener.",
      memory_filter: "chemistry\nopener",
    }),
    {rounds: 2, call_to_action: "Old CTA"},
  );

  assert.deepEqual(next, {
    pod_date: {
      rounds: 3,
      call_to_action: "New CTA",
      instructions_override: "Keep it more playful.",
      examples_override: "Exercise: Say something witty. --- Witty response.",
      context_override: "Keep the scene focused on immediate chemistry.",
      memory_override: "Only remember the last pod beat and the current opener.",
      memory_filter: "chemistry\nopener",
    },
  });
}

function testSceneTypeFormBlockDropsBlankLocalOverrides() {
  const next = applySceneTypeFormBlock(
    {
      pod_date: {
        rounds: 2,
        call_to_action: "Old CTA",
        instructions_override: "Old override",
        examples_override: "Old examples",
        context_override: "Old context",
        memory_override: "Old memory override",
        memory_filter: "Old memory filter",
      },
    },
    "pod_date",
    sceneTypeBlock({
      name: "pod_date",
      rounds: "2",
      call_to_action: "Old CTA",
      instructions_override: "   ",
      examples_override: "   ",
      context_override: "   ",
      memory_override: "   ",
      memory_filter: "   ",
    }),
    {
      rounds: 2,
      call_to_action: "Old CTA",
      instructions_override: "Old override",
      examples_override: "Old examples",
      context_override: "Old context",
      memory_override: "Old memory override",
      memory_filter: "Old memory filter",
    },
  );

  assert.deepEqual(next, {
    pod_date: {
      rounds: 2,
      call_to_action: "Old CTA",
    },
  });
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
testSceneTypeEditorIncludesInstructionsOverrideField();
testSceneTypeFormBlockPersistsInstructionsOverride();
testSceneTypeFormBlockDropsBlankLocalOverrides();
testRenderedSceneCollectionPreservesHiddenScenes();
console.log("app_scene_selector_test passed");
