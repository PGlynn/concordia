const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");

function tabLabels() {
  return [...html.matchAll(/<button data-tab="([^"]+)"(?: class="active")?>([^<]+)<\/button>/g)]
    .map((match) => ({id: match[1], label: match[2], active: match[0].includes('class="active"')}));
}

function testSimulationConfigIsLastSecondaryTab() {
  const tabs = tabLabels();

  assert.deepEqual(tabs.map((tab) => tab.id), [
    "dialogue",
    "candidates",
    "showFlow",
    "sceneEditor",
    "logs",
    "help",
    "config",
  ]);
  assert.equal(tabs[0].label, "Dialogue");
  assert.equal(tabs[0].active, true);
  assert.deepEqual(tabs.at(-1), {id: "config", label: "Simulation Config", active: false});
  assert.doesNotMatch(html, /data-tab="config"[^>]*>Config<\/button>/);
}

function testScenesAreSplitIntoUserFacingSurfaces() {
  assert.match(html, /data-tab="showFlow"[^>]*>Show Flow/);
  assert.match(html, /data-tab="sceneEditor"[^>]*>Scene Editor/);
  assert.match(html, /data-tab-panel="showFlow"/);
  assert.match(html, /data-tab-panel="sceneEditor"/);
  assert.doesNotMatch(html, /data-tab="scenes"[^>]*>Scenes/);
}

function testSnapshotLivesUnderLogs() {
  assert.doesNotMatch(html, /data-tab="snapshot"[^>]*>Snapshot/);
  assert.match(html, /data-logs-tab="browser"[^>]*>Log Browser/);
  assert.match(html, /data-logs-tab="snapshot"[^>]*>Snapshot/);
  assert.match(html, /data-logs-panel="snapshot"/);
}

function testSemanticsAreVisibleInUiCopy() {
  assert.match(html, /Chooses the two active contestants for this draft/);
  assert.match(html, /scene\.participants/);
  assert.match(html, /scene\.num_rounds/);
}

testSimulationConfigIsLastSecondaryTab();
testScenesAreSplitIntoUserFacingSurfaces();
testSnapshotLivesUnderLogs();
testSemanticsAreVisibleInUiCopy();
console.log("app_tab_structure_test passed");
