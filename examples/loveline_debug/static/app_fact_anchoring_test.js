const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const {
  __getTestState,
  __setTestState,
  collectConfigForm,
  renderConfigTab,
  runContextLabel,
  summarizeDraftContext,
} = require("./app.js");

const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");

function makeElement(initial = {}) {
  return {
    value: "",
    checked: false,
    innerHTML: "",
    ...initial,
  };
}

function withFakeDocument(elements, fn) {
  const previousDocument = global.document;
  global.document = {
    getElementById(id) {
      return elements[id] || null;
    },
  };
  try {
    fn();
  } finally {
    global.document = previousDocument;
  }
}

function testRunSettingsHtmlIncludesStrictFactAnchoringCheckbox() {
  assert.match(
    html,
    /id="strictCandidateFactAnchoring"[^>]*>\s*Strict candidate fact anchoring for selected contestants/
  );
}

function testRenderAndCollectConfigFormPersistStrictFactAnchoring() {
  const previousState = __getTestState();
  const draft = {
    schema_version: 1,
    name: "pair_debug",
    created_at: "2026-04-24T00:00:00+00:00",
    updated_at: "2026-04-24T00:00:00+00:00",
    source_root: "/tmp/starter",
    selected_candidate_ids: ["alex_id", "blake_id"],
    contestants: [
      {id: "alex_id", name: "Alex", gender: "man"},
      {id: "blake_id", name: "Blake", gender: "woman"},
    ],
    run: {
      max_steps: 8,
      disable_language_model: false,
      api_type: "ollama",
      model_name: "qwen3.5:35b-a3b",
      start_paused: true,
      checkpoint_every_step: true,
      strict_candidate_fact_anchoring: true,
    },
    scene_defaults: {
      main_game_master_name: "Show Runner",
      default_premise: "Default premise",
    },
    scenes: [],
  };
  const elements = {
    maleCandidate: makeElement(),
    femaleCandidate: makeElement(),
    schemaVersion: makeElement(),
    createdAt: makeElement(),
    updatedAt: makeElement(),
    sourceRootInput: makeElement(),
    mainGameMasterName: makeElement(),
    defaultPremise: makeElement(),
    maxSteps: makeElement(),
    disableLm: makeElement(),
    apiType: makeElement(),
    modelName: makeElement(),
    startPaused: makeElement(),
    checkpointEveryStep: makeElement(),
    skipGeneratedFormativeMemories: makeElement(),
    strictCandidateFactAnchoring: makeElement(),
    configRawJson: makeElement(),
    candidateTags: makeElement(),
    showFlowSummary: makeElement(),
  };

  __setTestState({
    draft,
    source: {starter_root: "/tmp/starter", candidates: []},
  });
  withFakeDocument(elements, () => {
    renderConfigTab();
    assert.equal(elements.strictCandidateFactAnchoring.checked, true);
    assert.equal(
      JSON.parse(elements.configRawJson.value).run.strict_candidate_fact_anchoring,
      true
    );

    elements.strictCandidateFactAnchoring.checked = false;
    collectConfigForm();

    assert.equal(
      __getTestState().draft.run.strict_candidate_fact_anchoring,
      false
    );
  });
  __setTestState(previousState);
}

function testSummaryAndHistoryLabelIncludeStrictFactAnchoring() {
  const summary = summarizeDraftContext({
    contestants: [{name: "Alex"}, {name: "Blake"}],
    scenes: [],
    run: {
      max_steps: 6,
      model_name: "qwen3.5:35b-a3b",
      strict_candidate_fact_anchoring: true,
    },
  });

  assert.equal(summary.strict_candidate_fact_anchoring, true);
  assert.equal(
    runContextLabel(summary),
    "Alex vs Blake | 6 steps | qwen3.5:35b-a3b | starts paused | checkpoints | strict fact anchors"
  );
}

testRunSettingsHtmlIncludesStrictFactAnchoringCheckbox();
testRenderAndCollectConfigFormPersistStrictFactAnchoring();
testSummaryAndHistoryLabelIncludeStrictFactAnchoring();
console.log("app_fact_anchoring_test passed");
