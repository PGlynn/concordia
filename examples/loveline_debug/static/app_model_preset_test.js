const assert = require("assert/strict");

const {
  DEFAULT_MODEL_PRESET,
  MODEL_PRESETS,
  applyModelPresetSelection,
  collectConfigForm,
  deriveModelPreset,
  modelPresetLabel,
  syncModelPresetControl,
  __getTestState,
  __setTestState,
} = require("./app.js");

function makeElements() {
  const elements = new Map([
    ["configRawJson", {value: "{}"}],
    ["schemaVersion", {value: "1"}],
    ["sourceRootInput", {value: "/starter"}],
    ["maleCandidate", {value: "alex_id"}],
    ["femaleCandidate", {value: "blake_id"}],
    ["mainGameMasterName", {value: "Show Runner"}],
    ["defaultPremise", {value: ""}],
    ["maxSteps", {value: "8"}],
    ["disableLm", {checked: false}],
    ["modelPreset", {value: DEFAULT_MODEL_PRESET, innerHTML: ""}],
    ["apiType", {value: MODEL_PRESETS.local_ollama.api_type}],
    ["modelName", {value: MODEL_PRESETS.local_ollama.model_name}],
    ["startPaused", {checked: true}],
    ["checkpointEveryStep", {checked: true}],
    ["skipGeneratedFormativeMemories", {checked: false}],
    ["strictCandidateFactAnchoring", {checked: false}],
  ]);
  global.document = {
    activeElement: null,
    getElementById(id) {
      return elements.get(id) || null;
    },
    querySelectorAll() {
      return [];
    },
  };
  return elements;
}

function testPresetHelpersExposeExpectedRoutes() {
  assert.equal(DEFAULT_MODEL_PRESET, "local_ollama");
  assert.equal(MODEL_PRESETS.local_ollama.model_name, "qwen3.5:35b-a3b");
  assert.equal(MODEL_PRESETS.codex_oauth.model_name, "gpt-5.4");
  assert.equal(deriveModelPreset(MODEL_PRESETS.local_ollama), "local_ollama");
  assert.equal(deriveModelPreset(MODEL_PRESETS.codex_oauth), "codex_oauth");
  assert.equal(
    deriveModelPreset({api_type: "codex_oauth", model_name: "gpt-5.5"}),
    "custom",
  );
  assert.equal(modelPresetLabel(MODEL_PRESETS.codex_oauth), "Codex OAuth");
}

function testApplyingPresetUpdatesExplicitFields() {
  const elements = makeElements();

  applyModelPresetSelection("codex_oauth");

  assert.equal(elements.get("apiType").value, "codex_oauth");
  assert.equal(elements.get("modelName").value, "gpt-5.4");
  assert.equal(elements.get("modelPreset").value, "codex_oauth");
  delete global.document;
}

function testCollectConfigFormStoresCustomPresetWhenFieldsDiverge() {
  makeElements();
  __setTestState({
    draft: {
      schema_version: 1,
      created_at: "created",
      updated_at: "updated",
      source_root: "/starter",
      selected_candidate_ids: ["alex_id", "blake_id"],
      scene_defaults: {},
      run: {},
    },
    source: {starter_root: "/starter"},
  });
  global.document.getElementById("modelPreset").value = "codex_oauth";
  global.document.getElementById("apiType").value = "codex_oauth";
  global.document.getElementById("modelName").value = "gpt-5.5";

  collectConfigForm();

  assert.equal(__getTestState().draft.run.model_preset, "custom");
  assert.equal(__getTestState().draft.run.api_type, "codex_oauth");
  assert.equal(__getTestState().draft.run.model_name, "gpt-5.5");
  delete global.document;
}

function testSyncModelPresetControlReflectsManualOverrides() {
  const elements = makeElements();

  syncModelPresetControl({api_type: "codex_oauth", model_name: "gpt-5.5"});

  assert.match(elements.get("modelPreset").innerHTML, /Local Ollama/);
  assert.match(elements.get("modelPreset").innerHTML, /Codex OAuth/);
  assert.match(elements.get("modelPreset").innerHTML, />Custom</);
  assert.equal(elements.get("modelPreset").value, "custom");
  delete global.document;
}

testPresetHelpersExposeExpectedRoutes();
testApplyingPresetUpdatesExplicitFields();
testCollectConfigFormStoresCustomPresetWhenFieldsDiverge();
testSyncModelPresetControlReflectsManualOverrides();
console.log("app_model_preset_test passed");
