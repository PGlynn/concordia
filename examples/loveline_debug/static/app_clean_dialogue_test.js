const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const {
  cleanDialogueContext,
  cleanDialogueEntries,
  cleanDialogueStepLabel,
  cleanDialogueText,
  stripDialogueSpeakerPrefix,
  activeDialogueState,
  completedDialogueHandoffRunId,
  followedActiveDialogueRunId,
  renderCleanDialogue,
} = require("./app.js");

function installDom() {
  const elements = new Map();
  for (const id of ["cleanDialogueContext", "cleanDialogueView", "cleanDialogueMessage", "cleanDialogueRunSelect"]) {
    elements.set(id, {
      innerHTML: "",
      textContent: "",
      className: "",
      value: "",
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
      raw_utterance_text: "Alex: Alex: I want the real thing.",
      concordia_event_text: "Alex: Alex: I want the real thing.",
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

function testIndexExposesDialogueAsPrimaryTab() {
  const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
  const configIndex = html.indexOf('data-tab="config"');
  const dialogueIndex = html.indexOf('data-tab="dialogue"');
  const candidatesIndex = html.indexOf('data-tab="candidates"');

  assert.ok(configIndex > -1);
  assert.ok(dialogueIndex > -1);
  assert.ok(candidatesIndex > dialogueIndex);
  assert.ok(configIndex > candidatesIndex);
  assert.match(html, /data-tab-panel="dialogue"/);
}

function testCleanDialogueFiltersCandidateDialogueOnly() {
  const entries = cleanDialogueEntries(state);

  assert.equal(entries.length, 2);
  assert.equal(entries[0].entity_name, "Alex");
  assert.equal(entries[1].entity_name, "Blake");
  assert.equal(cleanDialogueText(entries[0]), "I want the real thing.");
}

function testCleanDialogueContextPrefersStateSummary() {
  assert.deepEqual(cleanDialogueContext(state, {recent_runs: []}).selected_pair, ["Alex", "Blake"]);
}

function testRenderCleanDialogueShowsContextAndConversation() {
  const elements = installDom();
  renderCleanDialogue(state);

  assert.match(elements.get("cleanDialogueContext").innerHTML, /run_1/);
  assert.match(elements.get("cleanDialogueContext").innerHTML, /Alex vs Blake/);
  assert.match(elements.get("cleanDialogueContext").innerHTML, /Configured Scenes/);
  assert.match(elements.get("cleanDialogueView").innerHTML, /dialogue-turn/);
  assert.match(elements.get("cleanDialogueView").innerHTML, /Spoken turn 1/);
  assert.doesNotMatch(elements.get("cleanDialogueView").innerHTML, /engine step/);
  assert.match(elements.get("cleanDialogueView").innerHTML, />I want the real thing\.</);
  assert.match(elements.get("cleanDialogueView").innerHTML, /Show raw utterance/);
  assert.match(elements.get("cleanDialogueView").innerHTML, /<details class="dialogue-raw">/);
  assert.match(elements.get("cleanDialogueView").innerHTML, /Alex: Alex: I want the real thing/);
  assert.match(elements.get("cleanDialogueView").innerHTML, /That means a lot to hear/);
  assert.doesNotMatch(elements.get("cleanDialogueView").innerHTML, /The date continues/);
}

function testCleanDialogueHidesEngineStepWhenFirstSpeechStartsAtStepTwo() {
  const elements = installDom();
  renderCleanDialogue({
    ...state,
    entries: [
      {...state.entries[0], step: 2},
      {...state.entries[1], step: 1},
      {...state.entries[2], step: 3},
    ],
  });

  assert.doesNotMatch(elements.get("cleanDialogueView").innerHTML, /First spoken turn is engine step 2/);
  assert.doesNotMatch(elements.get("cleanDialogueView").innerHTML, /engine step 2/);
  assert.equal(cleanDialogueStepLabel({step: 2}, 0), "Spoken turn 1");
}

function testStripDialogueSpeakerPrefixRemovesRepeatedLabelOnly() {
  assert.equal(
    stripDialogueSpeakerPrefix("Lena Park: Lena Park: Hi there.", "Lena Park"),
    "Hi there."
  );
  assert.equal(
    stripDialogueSpeakerPrefix("Marcus Vale: Hello there.", "Lena Park"),
    "Marcus Vale: Hello there."
  );
}

function testRenderCleanDialogueCanFollowActiveRun() {
  const elements = installDom();
  const state = activeDialogueState({
    active: {
      run_id: "active_run",
      status: "running",
      summary: {
        selected_pair: ["Alex", "Blake"],
        scene_count: 2,
        total_configured_rounds: 3,
      },
      transcript: [
        {step: 1, acting_entity: "Alex", action: "I am here live."},
      ],
    },
  });

  assert.equal(state.live, true);
  assert.equal(state.run_id, "active_run");
  assert.equal(cleanDialogueStepLabel(state.entries[0], 0), "Live step 1");
  assert.equal(cleanDialogueText(state.entries[0]), "I am here live.");

  renderCleanDialogue(state);
  assert.match(elements.get("cleanDialogueContext").innerHTML, /live status transcript/);
  assert.match(elements.get("cleanDialogueContext").innerHTML, /Configured Rounds/);
  assert.match(elements.get("cleanDialogueView").innerHTML, /Live step 1/);
  assert.match(elements.get("cleanDialogueView").innerHTML, /I am here live/);
}

function testCompletedRunHandoffKeepsFollowingTheSameRun() {
  const elements = installDom();
  elements.get("cleanDialogueRunSelect").value = "__active__";

  const followedRunId = followedActiveDialogueRunId(
    {
      active: {
        run_id: "run_live",
        status: "running",
      },
    },
    null,
    "__active__"
  );

  assert.equal(followedRunId, "run_live");
  assert.equal(completedDialogueHandoffRunId(followedRunId, {
    active: {
      run_id: "run_live",
      status: "completed",
      artifacts: {
        structured_log: "/tmp/run_live/structured_log.json",
      },
    },
  }), "run_live");
  assert.equal(completedDialogueHandoffRunId(followedRunId, {
    active: {
      run_id: "run_live",
      status: "completed",
      artifacts: {},
    },
  }), "");
}

testIndexExposesDialogueAsPrimaryTab();
testCleanDialogueFiltersCandidateDialogueOnly();
testCleanDialogueContextPrefersStateSummary();
testRenderCleanDialogueShowsContextAndConversation();
testCleanDialogueHidesEngineStepWhenFirstSpeechStartsAtStepTwo();
testStripDialogueSpeakerPrefixRemovesRepeatedLabelOnly();
testRenderCleanDialogueCanFollowActiveRun();
testCompletedRunHandoffKeepsFollowingTheSameRun();
console.log("app_clean_dialogue_test passed");
