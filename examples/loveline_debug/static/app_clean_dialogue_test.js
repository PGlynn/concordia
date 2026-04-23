const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const {
  cleanDialogueContext,
  cleanDialogueEntries,
  cleanDialogueStepLabel,
  cleanDialogueText,
  renderCleanDialogue,
} = require("./app.js");

function installDom() {
  const elements = new Map();
  for (const id of ["cleanDialogueContext", "cleanDialogueView", "cleanDialogueMessage"]) {
    elements.set(id, {
      innerHTML: "",
      textContent: "",
      className: "",
    });
  }
  global.document = {
    getElementById(id) {
      return elements.get(id) || null;
    },
  };
  return elements;
}

const state = {
  run_id: "run_1",
  available: true,
  summary: {
    selected_pair: ["Alex", "Blake"],
    max_steps: 8,
    model_name: "qwen3.5:35b-a3b",
    scene_count: 1,
  },
  entries: [
    {
      index: 0,
      step: 1,
      entry_type: "entity",
      entity_name: "Alex",
      raw_utterance_text: "I want the real thing.",
      concordia_event_text: "Alex: I want the real thing.",
    },
    {
      index: 1,
      step: 1,
      entry_type: "step",
      entity_name: "Show Runner",
      preview: "The date continues.",
    },
    {
      index: 2,
      step: 2,
      entry_type: "entity",
      entity_name: "Blake",
      preview: "That means a lot to hear.",
    },
  ],
};

function testIndexExposesDialogueTabNextToConfig() {
  const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
  const configIndex = html.indexOf('data-tab="config"');
  const dialogueIndex = html.indexOf('data-tab="dialogue"');
  const candidatesIndex = html.indexOf('data-tab="candidates"');

  assert.ok(configIndex > -1);
  assert.ok(dialogueIndex > configIndex);
  assert.ok(candidatesIndex > dialogueIndex);
  assert.match(html, /data-tab-panel="dialogue"/);
}

function testCleanDialogueFiltersCandidateDialogueOnly() {
  const entries = cleanDialogueEntries(state);

  assert.equal(entries.length, 2);
  assert.equal(entries[0].entity_name, "Alex");
  assert.equal(entries[1].entity_name, "Blake");
  assert.equal(cleanDialogueText(entries[0]), "Alex: I want the real thing.");
}

function testCleanDialogueContextPrefersStateSummary() {
  assert.deepEqual(cleanDialogueContext(state, {recent_runs: []}).selected_pair, ["Alex", "Blake"]);
}

function testRenderCleanDialogueShowsContextAndConversation() {
  const elements = installDom();
  renderCleanDialogue(state);

  assert.match(elements.get("cleanDialogueContext").innerHTML, /run_1/);
  assert.match(elements.get("cleanDialogueContext").innerHTML, /Alex vs Blake/);
  assert.match(elements.get("cleanDialogueView").innerHTML, /dialogue-turn/);
  assert.match(elements.get("cleanDialogueView").innerHTML, /Spoken turn 1 \| engine step 1/);
  assert.match(elements.get("cleanDialogueView").innerHTML, /Alex: I want the real thing/);
  assert.match(elements.get("cleanDialogueView").innerHTML, /Raw: I want the real thing/);
  assert.match(elements.get("cleanDialogueView").innerHTML, /That means a lot to hear/);
  assert.doesNotMatch(elements.get("cleanDialogueView").innerHTML, /The date continues/);
}

function testCleanDialogueShowsEngineStepWhenFirstSpeechStartsAtStepTwo() {
  const elements = installDom();
  renderCleanDialogue({
    ...state,
    entries: [
      {...state.entries[0], step: 2},
      {...state.entries[1], step: 1},
      {...state.entries[2], step: 3},
    ],
  });

  assert.match(elements.get("cleanDialogueView").innerHTML, /First spoken turn is engine step 2/);
  assert.match(elements.get("cleanDialogueView").innerHTML, /Spoken turn 1 \| engine step 2/);
  assert.equal(cleanDialogueStepLabel({step: 2}, 0), "Spoken turn 1 | engine step 2");
}

testIndexExposesDialogueTabNextToConfig();
testCleanDialogueFiltersCandidateDialogueOnly();
testCleanDialogueContextPrefersStateSummary();
testRenderCleanDialogueShowsContextAndConversation();
testCleanDialogueShowsEngineStepWhenFirstSpeechStartsAtStepTwo();
console.log("app_clean_dialogue_test passed");
