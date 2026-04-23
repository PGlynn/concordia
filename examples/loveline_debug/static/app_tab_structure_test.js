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

function testDialogueOwnsRunWorkflowSubmodes() {
  assert.doesNotMatch(html, /data-tab="snapshot"[^>]*>Snapshot/);
  assert.doesNotMatch(html, /data-tab="logs"[^>]*>Logs/);
  assert.match(html, /data-dialogue-tab="conversation"[^>]*>Conversation/);
  assert.match(html, /data-dialogue-tab="compare"[^>]*>Compare/);
  assert.match(html, /data-dialogue-tab="inspect"[^>]*>Inspect/);
  assert.match(html, /data-dialogue-tab="browser"[^>]*>Log Browser/);
  assert.match(html, /id="compareLeft"/);
  assert.match(html, /id="compareRight"/);
  assert.doesNotMatch(html, /Use as A/);
  assert.doesNotMatch(html, /Use as B/);
}

function testTabsStayVisibleWhilePanelsScroll() {
  assert.match(html, /\.tabs \{[\s\S]*position: sticky;/);
  assert.match(html, /\.tabs \{[\s\S]*top: -14px;/);
}

function testSavedDraftPickerLivesInHeader() {
  const header = html.match(/<header>([\s\S]*?)<\/header>/)[1];
  const firstSection = html.match(/<main>[\s\S]*?<section>([\s\S]*?)<\/section>/)[1];

  assert.match(header, /<select id="loadDraft">/);
  assert.match(header, /id="createDraft"/);
  assert.doesNotMatch(header, /id="loadDraftBtn"/);
  assert.doesNotMatch(firstSection, /<select id="loadDraft">/);
  assert.match(firstSection, /id="showFlowSummary"/);
  assert.match(firstSection, /Start Run From Current Draft/);
  assert.match(firstSection, /id="progressSummary"/);
}

function testConfigOwnsPairAndRestoreControls() {
  const firstSection = html.match(/<main>[\s\S]*?<section>([\s\S]*?)<\/section>/)[1];
  const configPanel = html.match(/<div data-tab-panel="config"[\s\S]*?<\/details>\s*<\/div>/)[0];

  assert.doesNotMatch(firstSection, /Restore \/ Reset/);
  assert.doesNotMatch(firstSection, /Selected Pair/);
  assert.doesNotMatch(firstSection, /id="candidateTags"/);
  assert.match(configPanel, /Selected Pair/);
  assert.match(configPanel, /Restore \/ Reset/);
  assert.match(configPanel, /id="candidateTags"/);
  assert.match(configPanel, /id="restoreSelection"/);
  assert.match(configPanel, /id="resetDefault"/);
}

function testSemanticsAreVisibleInUiCopy() {
  assert.match(html, /Chooses the two active contestants for this draft/);
  assert.match(html, /scene\.participants/);
  assert.match(html, /scene\.num_rounds/);
}

testSimulationConfigIsLastSecondaryTab();
testScenesAreSplitIntoUserFacingSurfaces();
testDialogueOwnsRunWorkflowSubmodes();
testTabsStayVisibleWhilePanelsScroll();
testSavedDraftPickerLivesInHeader();
testConfigOwnsPairAndRestoreControls();
testSemanticsAreVisibleInUiCopy();
console.log("app_tab_structure_test passed");
