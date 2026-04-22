const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const {stockFlowHelpHtml} = require("./app.js");

function testIndexExposesHelpTab() {
  const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");

  assert.match(html, /data-tab="help"/);
  assert.match(html, /data-tab-panel="help"/);
}

function testHelpRendersStockActorFlowAndToggleState() {
  const html = stockFlowHelpHtml({
    contestants: [
      {
        name: "Alex",
        entity_params: {
          stock_basic_entity_components: {
            SituationPerception: true,
            SelfPerception: false,
            PersonBySituation: true,
          },
        },
      },
    ],
  });

  assert.match(html, /Stock Actor Flow/);
  assert.match(html, /instructions -&gt; observation history \/ memory retrieval -&gt; SituationPerception -&gt; SelfPerception -&gt; PersonBySituation -&gt; ConcatActComponent -&gt; final action output/);
  assert.match(html, /generated summaries that condition the final act prompt/);
  assert.match(html, /Current Stock Question Toggles/);
  assert.match(html, /Alex/);
  assert.match(html, /Situation Perception: enabled/);
  assert.match(html, /Self Perception: disabled/);
  assert.match(html, /Person by Situation: enabled/);
}

testIndexExposesHelpTab();
testHelpRendersStockActorFlowAndToggleState();
console.log("app_flow_help_test passed");
