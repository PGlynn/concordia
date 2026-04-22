const assert = require("assert/strict");

const {
  formatLogDetails,
  logSearchText,
  renderCompareSide,
  renderLogBrowser,
  renderTurnDetail,
} = require("./app.js");

function installLogDom() {
  const elements = new Map();
  for (const id of ["logFilter", "logEntries", "logDetails", "logMessage", "logArtifactLink"]) {
    elements.set(id, {
      value: "",
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

const turn = {
  step: 1,
  entity_name: "Alex",
  summary: "Alex speaks",
  action: "Alex: I want the real thing.",
  raw_utterance_text: "I want the real thing.",
  concordia_event_text: "Alex: I want the real thing.",
  action_prompt: "Answer honestly.",
  observations: [],
  components: [],
  entity_memories: [],
  game_master_entries: [],
  game_master_memories: [],
  raw_entry: {data: {value: {__act__: {Value: "Alex: I want the real thing."}}}},
};

function testTurnInspectorLabelsRawAndConcordiaTextSeparately() {
  const html = renderTurnDetail(turn, {run_id: "run_1"});

  assert.match(html, /Raw Utterance Text/);
  assert.match(html, /I want the real thing/);
  assert.match(html, /Concordia Event \/ Display Text/);
  assert.match(html, /Alex: I want the real thing/);
}

function testCompareSideUsesExplicitTextLabels() {
  const html = renderCompareSide("Left", {
    run_id: "run_1",
    config: {candidates: ["Alex", "Blake"]},
    first_turn: turn,
    transcript: [],
  });

  assert.match(html, /Raw Utterance Text/);
  assert.match(html, /Concordia Event \/ Display Text/);
  assert.match(html, /Alex: I want the real thing/);
}

function testLogDetailsAndSearchIncludeBothTextSurfaces() {
  const entry = {
    index: 0,
    step: 1,
    entity_name: "Alex",
    component_name: "entity_action",
    entry_type: "entity",
    summary: "Alex speaks",
    preview: "Alex: I want the real thing.",
    raw_utterance_text: "I want the real thing.",
    concordia_event_text: "Alex: I want the real thing.",
    raw_entry: {data: {value: {__act__: {Value: "Alex: I want the real thing."}}}},
  };

  assert.match(logSearchText(entry), /raw|i want the real thing/);
  assert.match(formatLogDetails(entry), /Raw utterance text:\nI want the real thing/);
  assert.match(formatLogDetails(entry), /Concordia event\/display text:\nAlex: I want the real thing/);
}

function testLogTableShowsExplicitLabels() {
  const elements = installLogDom();
  renderLogBrowser({
    run_id: "run_1",
    available: true,
    entry_count: 1,
    entries: [{
      index: 0,
      step: 1,
      entity_name: "Alex",
      component_name: "entity_action",
      entry_type: "entity",
      summary: "Alex speaks",
      raw_utterance_text: "I want the real thing.",
      concordia_event_text: "Alex: I want the real thing.",
      raw_entry: {data: {value: "Alex: I want the real thing."}},
    }],
    artifacts: {},
  });

  assert.match(elements.get("logEntries").innerHTML, /Raw utterance:/);
  assert.match(elements.get("logEntries").innerHTML, /Concordia event\/display:/);
  assert.match(elements.get("logDetails").textContent, /Raw utterance text:/);
}

testTurnInspectorLabelsRawAndConcordiaTextSeparately();
testCompareSideUsesExplicitTextLabels();
testLogDetailsAndSearchIncludeBothTextSurfaces();
testLogTableShowsExplicitLabels();
console.log("app_raw_text_test passed");
