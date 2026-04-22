const assert = require("assert/strict");

const {
  draftFingerprint,
  runContextLabel,
  summarizeDraftContext,
} = require("./app.js");

function testDraftFingerprintIgnoresObjectKeyOrder() {
  const left = {
    name: "draft",
    run: {model_name: "gpt-4o", max_steps: 8},
    contestants: [{name: "Alex", id: "a"}],
  };
  const right = {
    contestants: [{id: "a", name: "Alex"}],
    run: {max_steps: 8, model_name: "gpt-4o"},
    name: "draft",
  };

  assert.equal(draftFingerprint(left), draftFingerprint(right));
}

function testSummarizeDraftContextIncludesGuardrailMetadata() {
  const summary = summarizeDraftContext({
    source_root: "/starter",
    selected_candidate_ids: ["alex_id", "blake_id"],
    contestants: [{name: "Alex"}, {name: "Blake"}],
    scenes: [{id: "pod"}],
    run: {
      max_steps: 9,
      disable_language_model: true,
      api_type: "openai",
      model_name: "gpt-4o",
      start_paused: false,
      checkpoint_every_step: false,
    },
  });

  assert.deepEqual(summary.selected_pair, ["Alex", "Blake"]);
  assert.deepEqual(summary.selected_candidate_ids, ["alex_id", "blake_id"]);
  assert.equal(summary.scene_count, 1);
  assert.equal(summary.max_steps, 9);
  assert.equal(summary.disable_language_model, true);
  assert.equal(summary.start_paused, false);
  assert.equal(summary.checkpoint_every_step, false);
}

function testRunContextLabelMakesRecentRunsReadable() {
  const label = runContextLabel({
    selected_pair: ["Alex", "Blake"],
    max_steps: 9,
    disable_language_model: true,
    start_paused: false,
    checkpoint_every_step: false,
  });

  assert.equal(label, "Alex vs Blake | 9 steps | LM disabled | starts playing | no checkpoints");
}

testDraftFingerprintIgnoresObjectKeyOrder();
testSummarizeDraftContextIncludesGuardrailMetadata();
testRunContextLabelMakesRecentRunsReadable();
console.log("app_guardrails_test passed");
