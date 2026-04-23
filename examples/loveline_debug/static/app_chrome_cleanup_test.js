const assert = require("assert/strict");

const {
  renderRecentRuns,
  renderCompareSide,
  showFlowSummaryHtml,
} = require("./app.js");

function installRecentRunsDom() {
  const elements = new Map();
  for (const id of ["recentRuns", "compareLeft", "compareRight", "logRunSelect", "cleanDialogueRunSelect"]) {
    elements.set(id, {
      innerHTML: "",
      value: "",
    });
  }
  global.document = {
    getElementById(id) {
      return elements.get(id) || null;
    },
  };
  return elements;
}

function testRecentRunCompareAffordancesNameSideInputs() {
  const elements = installRecentRunsDom();
  renderRecentRuns([
    {run_id: "run_a", status: "done", artifacts: {}, summary: {}},
    {run_id: "run_b", status: "done", artifacts: {}, summary: {}},
  ]);

  const html = elements.get("recentRuns").innerHTML;
  assert.match(html, /Use as A/);
  assert.match(html, /Use as B/);
  assert.match(html, /compare side A/);
  assert.match(html, /compare side B/);
  assert.doesNotMatch(html, />Left<\/button>/);
  assert.doesNotMatch(html, />Right<\/button>/);
}

function testCompareSideUsesSceneCountLabel() {
  const html = renderCompareSide("Side A", {
    run_id: "run_a",
    config: {candidates: ["Alex", "Blake"], scene_count: 3},
    first_turn: null,
    transcript: [],
  });

  assert.match(html, /Side A/);
  assert.match(html, /Scene Count/);
  assert.doesNotMatch(html, />Scenes<\/dt>/);
}

function testShowFlowSummaryListsUsefulSceneMetadata() {
  const html = showFlowSummaryHtml({
    contestants: [{name: "Alex"}, {name: "Blake"}],
    scene_defaults: {main_game_master_name: "Show Runner"},
    scene_types: {pod_date: {rounds: 2}},
    scenes: [
      {id: "pod_intro", type: "pod_date", participants: ["Alex", "Blake"]},
      {id: "proposal", type: "proposal", num_rounds: 1, participants: ["Blake"]},
    ],
  });

  assert.match(html, /Scene Count/);
  assert.match(html, /Alex vs Blake/);
  assert.match(html, /pod_intro/);
  assert.match(html, /2 rounds/);
  assert.match(html, /proposal/);
  assert.match(html, /Blake/);
}

testRecentRunCompareAffordancesNameSideInputs();
testCompareSideUsesSceneCountLabel();
testShowFlowSummaryListsUsefulSceneMetadata();
console.log("app_chrome_cleanup_test passed");
