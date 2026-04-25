const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const {
  DEFAULT_API_TYPE,
  DEFAULT_MODEL_NAME,
  DEFAULT_MODEL_PRESET,
  draftFingerprint,
  formatRunTimestamp,
  renderDialogueRunWorkflow,
  runDraftIdentity,
  runContextLabel,
  runOptionLabel,
  summarizeDraftContext,
} = require("./app.js");

function testBrowserFallbackRunSettingsUseLocalLovelineModel() {
  assert.equal(DEFAULT_API_TYPE, "ollama");
  assert.equal(DEFAULT_MODEL_NAME, "qwen3.5:35b-a3b");
  assert.equal(DEFAULT_MODEL_PRESET, "local_ollama");
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
      model_preset: "codex_oauth",
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
  assert.equal(summary.model_preset, "local_ollama");
  assert.equal(summary.model_preset_label, "Local Ollama");
  assert.equal(summary.start_paused, false);
  assert.equal(summary.checkpoint_every_step, false);
}

function testRunContextLabelMakesRecentRunsReadable() {
  const label = runContextLabel({
    selected_pair: ["Alex", "Blake"],
    max_steps: 9,
    disable_language_model: false,
    model_preset_label: "Local Ollama",
    model_name: "qwen3.5:35b-a3b",
    start_paused: false,
    checkpoint_every_step: false,
  });

  assert.equal(label, "Alex vs Blake | 9 steps | Local Ollama | qwen3.5:35b-a3b | starts playing | no checkpoints");
}

function testRunContextLabelKeepsSmokeModeReadable() {
  const label = runContextLabel({
    selected_pair: ["Alex", "Blake"],
    max_steps: 9,
    disable_language_model: true,
  });

  assert.equal(label, "Alex vs Blake | 9 steps | LM disabled | starts paused | checkpoints");
}

function testRunDraftIdentityPrefersStableFilenameWhenAvailable() {
  assert.equal(
    runDraftIdentity({
      draft_filename: "alex_blake_experiment.json",
      draft_name: "alex_blake_experiment",
      name: "stale-name",
    }),
    "alex_blake_experiment.json",
  );
  assert.equal(runDraftIdentity({draft_name: "alex_blake_experiment"}), "alex_blake_experiment");
}

function testFormatRunTimestampMakesIsoReadable() {
  assert.equal(
    formatRunTimestamp("2026-04-21T22:15:00+00:00"),
    "Apr 21, 2026, 10:15 PM UTC",
  );
}

function testRunOptionLabelIncludesDraftIdentityAndTimestamp() {
  const label = runOptionLabel({
    run_id: "20260421_221500",
    status: "completed",
    started_at: "2026-04-21T22:15:00+00:00",
    summary: {
      draft_name: "alex_blake_experiment",
      selected_pair: ["Alex", "Blake"],
    },
  });

  assert.equal(
    label,
    "alex_blake_experiment - Apr 21, 2026, 10:15 PM UTC - completed - Alex vs Blake - 20260421_221500",
  );
}

function testConversationSelectorUsesExpandedActiveRunLabel() {
  const elements = new Map();
  for (const id of [
    "compareLeft",
    "compareRight",
    "logRunSelect",
    "cleanDialogueRunSelect",
    "inspectorRunSelect",
  ]) {
    elements.set(id, {value: "", innerHTML: ""});
  }
  global.document = {
    activeElement: null,
    getElementById(id) {
      return elements.get(id) || null;
    },
  };

  renderDialogueRunWorkflow([], {
    run_id: "20260421_221500",
    status: "running",
    started_at: "2026-04-21T22:15:00+00:00",
    summary: {
      draft_name: "alex_blake_experiment",
      selected_pair: ["Alex", "Blake"],
    },
  });

  assert.match(
    elements.get("cleanDialogueRunSelect").innerHTML,
    /Active run - alex_blake_experiment - Apr 21, 2026, 10:15 PM UTC - running - Alex vs Blake - 20260421_221500/,
  );
  delete global.document;
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
testRunDraftIdentityPrefersStableFilenameWhenAvailable();
testFormatRunTimestampMakesIsoReadable();
testRunOptionLabelIncludesDraftIdentityAndTimestamp();
testConversationSelectorUsesExpandedActiveRunLabel();
testMetadataFieldsAreReadOnlyInNormalForm();
console.log("app_guardrails_test passed");
