const assert = require("assert/strict");

const {renderCompareSide, renderTurnDetail} = require("./app.js");

function testRenderTurnDetailShowsDebugFields() {
  const html = renderTurnDetail(
    {
      step: 3,
      entity_name: "Alex",
      summary: "Alex speaks",
      action: "I am here for something real.",
      raw_utterance_text: "I am here for something real.",
      concordia_event_text: "Alex: I am here for something real.",
      action_prompt: ["Instructions:", "Answer honestly."],
      observations: ["[observation] Blake asked about commitment."],
      components: [{name: "Goal", value: "Find a serious match."}],
      entity_memories: ["Alex wants marriage."],
      game_master_entries: [
        {
          entity_name: "Show Runner",
          summary: "Show Runner resolves Alex",
          data: {event_resolution: {Value: "Blake hears Alex's answer."}},
        },
      ],
      game_master_memories: ["The pod date started."],
      raw_entry: {entry_type: "entity"},
    },
    {run_id: "run_1"}
  );

  assert.match(html, /Action Prompt/);
  assert.match(html, /Blake asked about commitment/);
  assert.match(html, /Component Outputs/);
  assert.match(html, /Find a serious match/);
  assert.match(html, /GM Reaction \/ Context/);
  assert.match(html, /Blake hears Alex&#039;s answer|Blake hears Alex's answer/);
}

testRenderTurnDetailShowsDebugFields();

function testRenderCompareSideShowsFirstTurnAndTranscript() {
  const html = renderCompareSide("Left", {
    run_id: "run_1",
    config: {
      candidates: ["Alex", "Blake"],
      scene_count: 1,
      max_steps: 8,
      disable_language_model: true,
    },
    first_turn: {
      step: 1,
      entity_name: "Alex",
      action: "I am ready.",
      raw_utterance_text: "I am ready.",
      concordia_event_text: "Alex: I am ready.",
      observations: ["Blake enters the pod."],
      components: [{name: "Goal", value: "Find a match."}],
    },
    transcript: [{step: 1, acting_entity: "Alex", action: "I am ready."}],
  });

  assert.match(html, /Alex vs Blake/);
  assert.match(html, /Raw Utterance Text/);
  assert.match(html, /Concordia Event \/ Display Text/);
  assert.match(html, /I am ready/);
  assert.match(html, /Transcript/);
}

testRenderCompareSideShowsFirstTurnAndTranscript();
console.log("app_inspector_render_test passed");
