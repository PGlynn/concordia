const assert = require("assert/strict");

const {
  filteredLogEntries,
  logSearchText,
  renderLogBrowser,
} = require("./app.js");

function installDom(filter = "") {
  const elements = new Map();
  for (const id of ["logFilter", "logEntries", "logDetails", "logMessage", "logArtifactLink"]) {
    elements.set(id, {
      value: id === "logFilter" ? filter : "",
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
  entry_count: 2,
  artifacts: {
    html_log: "/tmp/loveline/runs/run_1/log.html",
    structured_log: "/tmp/loveline/runs/run_1/structured_log.json",
  },
  entries: [
    {
      index: 0,
      step: 1,
      timestamp: "2026-04-21T22:00:00+00:00",
      entity_name: "Alex",
      component_name: "entity_action",
      entry_type: "entity",
      summary: "Alex speaks",
      preview: "I am ready.",
      raw_entry: {data: {value: "I am ready."}},
    },
    {
      index: 1,
      step: 1,
      timestamp: "2026-04-21T22:00:01+00:00",
      entity_name: "Show Runner",
      component_name: "game_master",
      entry_type: "step",
      summary: "Resolves the turn",
      preview: "Blake hears Alex.",
      raw_entry: {data: {value: "Blake hears Alex."}},
    },
  ],
};

function testLogSearchCoversRawEntry() {
  assert.match(logSearchText(state.entries[1]), /blake hears alex/);
}

function testFilteredLogEntriesMatchesEntityAndRawJson() {
  assert.equal(filteredLogEntries(state, "show runner").length, 1);
  assert.equal(filteredLogEntries(state, "I am ready").length, 1);
  assert.equal(filteredLogEntries(state, "").length, 2);
}

function testRenderLogBrowserShowsTableLinksAndSelectedRawJson() {
  const elements = installDom("show runner");
  renderLogBrowser({...state});

  assert.match(elements.get("logMessage").textContent, /1 of 2 entries shown/);
  assert.match(elements.get("logArtifactLink").innerHTML, /Open saved HTML log viewer/);
  assert.match(elements.get("logArtifactLink").innerHTML, /run_1\/log.html/);
  assert.match(elements.get("logEntries").innerHTML, /Show Runner/);
  assert.doesNotMatch(elements.get("logEntries").innerHTML, /Alex speaks/);
  assert.match(elements.get("logDetails").textContent, /Blake hears Alex/);
}

testLogSearchCoversRawEntry();
testFilteredLogEntriesMatchesEntityAndRawJson();
testRenderLogBrowserShowsTableLinksAndSelectedRawJson();
console.log("app_logs_test passed");
