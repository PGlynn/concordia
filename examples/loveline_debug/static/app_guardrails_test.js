const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const {
  DEFAULT_API_TYPE,
  DEFAULT_MODEL_NAME,
  draftFingerprint,
  runContextLabel,
  summarizeDraftContext,
} = require("./app.js");

function testBrowserFallbackRunSettingsUseLocalLovelineModel() {
  assert.equal(DEFAULT_API_TYPE, "ollama");
  assert.equal(DEFAULT_MODEL_NAME, "qwen3.5:35b-a3b");
}

function testDraftFingerprintIgnoresObjectKeyOrder() {
  const left = {
    name: "draft",
    run: {model_name: "qwen3.5:35b-a3b", max_steps: 8},
    contestants: [{name: "Alex", id: "a"}],
  };
  const right = {
    contestants: [{id: "a", name: "Alex"}],
    run: {max_steps: 8, model_name: "qwen3.5:35b-a3b"},
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
      disable_language_model: false,
      api_type: "ollama",
      model_name: "qwen3.5:35b-a3b",
      start_paused: false,
      checkpoint_every_step: false,
    },
  });

  assert.deepEqual(summary.selected_pair, ["Alex", "Blake"]);
  assert.deepEqual(summary.selected_candidate_ids, ["alex_id", "blake_id"]);
  assert.equal(summary.scene_count, 1);
  assert.equal(summary.max_steps, 9);
  assert.equal(summary.disable_language_model, false);
  assert.equal(summary.start_paused, false);
  assert.equal(summary.checkpoint_every_step, false);
}

function testRunContextLabelMakesRecentRunsReadable() {
  const label = runContextLabel({
    selected_pair: ["Alex", "Blake"],
    max_steps: 9,
    disable_language_model: false,
    model_name: "qwen3.5:35b-a3b",
    start_paused: false,
    checkpoint_every_step: false,
  });

  assert.equal(label, "Alex vs Blake | 9 steps | qwen3.5:35b-a3b | starts playing | no checkpoints");
}

function testRunContextLabelKeepsSmokeModeReadable() {
  const label = runContextLabel({
    selected_pair: ["Alex", "Blake"],
    max_steps: 9,
    disable_language_model: true,
  });

  assert.equal(label, "Alex vs Blake | 9 steps | LM disabled | starts paused | checkpoints");
}

function testMetadataFieldsAreReadOnlyInNormalForm() {
  const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");

  assert.match(html, /<label>Created At<input id="createdAt" readonly aria-readonly="true"><\/label>/);
  assert.match(html, /<label>Updated At<input id="updatedAt" readonly aria-readonly="true"><\/label>/);
}

testBrowserFallbackRunSettingsUseLocalLovelineModel();
testDraftFingerprintIgnoresObjectKeyOrder();
testSummarizeDraftContextIncludesGuardrailMetadata();
testRunContextLabelMakesRecentRunsReadable();
testRunContextLabelKeepsSmokeModeReadable();
testMetadataFieldsAreReadOnlyInNormalForm();
console.log("app_guardrails_test passed");
