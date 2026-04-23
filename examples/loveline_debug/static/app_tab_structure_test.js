const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");

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

testScenesAreSplitIntoUserFacingSurfaces();
testSnapshotLivesUnderLogs();
testSemanticsAreVisibleInUiCopy();
console.log("app_tab_structure_test passed");
