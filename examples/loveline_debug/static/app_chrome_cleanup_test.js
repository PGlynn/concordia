const assert = require("assert/strict");

const {
  renderRecentRuns,
  renderCompareSide,
  renderProgressSummary,
  showFlowSummaryHtml,
} = require("./app.js");

function installRecentRunsDom() {
  const elements = new Map();
  for (const id of ["dialogueRunActions", "compareLeft", "compareRight", "logRunSelect", "cleanDialogueRunSelect", "inspectorRunSelect"]) {
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

function installProgressDom() {
  const elements = new Map([[
    "progressSummary",
    {innerHTML: ""},
  ]]);
  global.document = {
    getElementById(id) {
      return elements.get(id) || null;
    },
  };
  return elements;
}

function testRecentRunActionsMoveIntoDialogueWorkflow() {
  const elements = installRecentRunsDom();
  renderRecentRuns([
    {run_id: "run_a", status: "done", artifacts: {}, summary: {}},
    {run_id: "run_b", status: "done", artifacts: {}, summary: {}},
  ]);

  const html = elements.get("dialogueRunActions").innerHTML;
  assert.match(html, /Saved Runs/);
  assert.match(html, /Open in Inspect/);
  assert.match(html, /Open Conversation/);
  assert.match(html, /Open Log/);
  assert.doesNotMatch(html, /Use as A/);
  assert.doesNotMatch(html, /Use as B/);
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

function testProgressSummaryUsesConfiguredShowFlowHonestly() {
  const elements = installProgressDom();
  renderProgressSummary({
    active: {
      status: "running",
      current_step: 2,
      summary: {
        max_steps: 8,
        scene_count: 2,
        total_configured_rounds: 3,
        show_flow: [
          {id: "confessional_marcus_after_round_one", rounds: 1},
          {id: "pod_date", rounds: 2},
        ],
      },
    },
    control: {current_step: 2},
  });

  const html = elements.get("progressSummary").innerHTML;
  assert.match(html, /Processing active run/);
  assert.match(html, /Engine step 2 of 8/);
  assert.doesNotMatch(html, /2 configured scenes, 3 configured rounds/);
  assert.doesNotMatch(html, /Exact active scene\/round is not emitted/);
}

testRecentRunActionsMoveIntoDialogueWorkflow();
testCompareSideUsesSceneCountLabel();
testShowFlowSummaryListsUsefulSceneMetadata();
testProgressSummaryUsesConfiguredShowFlowHonestly();
console.log("app_chrome_cleanup_test passed");
