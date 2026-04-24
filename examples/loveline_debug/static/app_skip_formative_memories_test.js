const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const {
  __getTestState,
  __setTestState,
  collectConfigForm,
  renderConfigTab,
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

function testRunSettingsHtmlIncludesSkipGeneratedFormativeMemoriesCheckbox() {
  assert.match(
    html,
    /id="skipGeneratedFormativeMemories"[^>]*>\s*Skip generated formative memories for selected contestants/
  );
}

function testRenderAndCollectConfigFormPersistSkipGeneratedFormativeMemories() {
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
      skip_generated_formative_memories: true,
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
    assert.equal(elements.skipGeneratedFormativeMemories.checked, true);
    assert.equal(
      JSON.parse(elements.configRawJson.value).run.skip_generated_formative_memories,
      true
    );

    elements.skipGeneratedFormativeMemories.checked = false;
    collectConfigForm();

    assert.equal(
      __getTestState().draft.run.skip_generated_formative_memories,
      false
    );
  });
  __setTestState(previousState);
}

testRunSettingsHtmlIncludesSkipGeneratedFormativeMemoriesCheckbox();
testRenderAndCollectConfigFormPersistSkipGeneratedFormativeMemories();
console.log("app_skip_formative_memories_test passed");
