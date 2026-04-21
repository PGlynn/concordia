const assert = require("assert/strict");

const {renderTurnDetail} = require("./app.js");

function testRenderTurnDetailShowsDebugFields() {
  const html = renderTurnDetail(
    {
      step: 3,
      entity_name: "Alex",
      summary: "Alex speaks",
      action: "I am here for something real.",
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
console.log("app_inspector_render_test passed");
