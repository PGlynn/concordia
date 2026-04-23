const assert = require("assert/strict");

const {
  renderDialogueRunWorkflow,
} = require("./app.js");

function makeSelect(value = "") {
  let html = "";
  return {
    value,
    writes: 0,
    get innerHTML() {
      return html;
    },
    set innerHTML(next) {
      this.writes += 1;
      html = next;
    },
  };
}

function installRunSelectDom() {
  const elements = new Map();
  elements.set("dialogueRunActions", {innerHTML: ""});
  for (const id of [
    "compareLeft",
    "compareRight",
    "logRunSelect",
    "cleanDialogueRunSelect",
    "inspectorRunSelect",
  ]) {
    elements.set(id, makeSelect());
  }
  global.document = {
    activeElement: null,
    getElementById(id) {
      return elements.get(id) || null;
    },
  };
  return elements;
}

const runA = {
  run_id: "run_a",
  status: "done",
  artifacts: {structured_log: "/tmp/run_a/structured_log.json"},
  summary: {selected_pair: ["Alex", "Blake"]},
};
const runB = {
  run_id: "run_b",
  status: "done",
  artifacts: {structured_log: "/tmp/run_b/structured_log.json"},
  summary: {selected_pair: ["Casey", "Drew"]},
};

function testStatusPollDoesNotRewriteUnchangedSelects() {
  const elements = installRunSelectDom();
  renderDialogueRunWorkflow([runA, runB]);
  const firstWrites = elements.get("logRunSelect").writes;
  elements.get("logRunSelect").value = "run_b";

  renderDialogueRunWorkflow([runA, runB]);

  assert.equal(elements.get("logRunSelect").writes, firstWrites);
  assert.equal(elements.get("logRunSelect").value, "run_b");
  assert.equal(elements.get("compareLeft").writes, 1);
  assert.equal(elements.get("compareRight").writes, 1);
  assert.equal(elements.get("cleanDialogueRunSelect").writes, 1);
  assert.equal(elements.get("inspectorRunSelect").writes, 1);
}

function testFocusedSelectIsNotClobberedByChangedRuns() {
  const elements = installRunSelectDom();
  const select = elements.get("logRunSelect");
  renderDialogueRunWorkflow([runA]);
  select.value = "run_a";
  global.document.activeElement = select;
  const firstWrites = select.writes;

  renderDialogueRunWorkflow([runA, runB]);

  assert.equal(select.writes, firstWrites);
  assert.equal(select.value, "run_a");

  global.document.activeElement = null;
  renderDialogueRunWorkflow([runA, runB]);

  assert.equal(select.writes, firstWrites + 1);
  assert.equal(select.value, "run_a");
}

testStatusPollDoesNotRewriteUnchangedSelects();
testFocusedSelectIsNotClobberedByChangedRuns();
console.log("app_select_stability_test passed");
