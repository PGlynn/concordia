const assert = require("assert/strict");

const {
  STOCK_BASIC_ENTITY_COMPONENT_FIELDS,
  collectStockBasicEntityComponentSettings,
  stockBasicEntityComponentSettings,
  stockBasicEntityComponentTogglesHtml,
} = require("./app.js");

function testComponentFieldsAreConstrainedToStockQuestionSet() {
  assert.deepEqual(
    STOCK_BASIC_ENTITY_COMPONENT_FIELDS.map(([key]) => key),
    ["SituationPerception", "SelfPerception", "PersonBySituation"],
  );
}

function testMissingComponentSettingsDefaultEnabled() {
  assert.deepEqual(stockBasicEntityComponentSettings({}), {
    SituationPerception: true,
    SelfPerception: true,
    PersonBySituation: true,
  });
}

function testToggleHtmlRendersNamedCheckboxes() {
  const html = stockBasicEntityComponentTogglesHtml({
    stock_basic_entity_components: {
      SituationPerception: false,
      SelfPerception: true,
      PersonBySituation: false,
    },
  });

  assert.match(html, /data-candidate-field="SituationPerception"/);
  assert.match(html, /data-candidate-field="SelfPerception" checked/);
  assert.match(html, /data-candidate-field="PersonBySituation"/);
}

function testCollectComponentSettingsUsesCheckboxState() {
  const checked = {
    SituationPerception: {checked: false},
    SelfPerception: {checked: true},
    PersonBySituation: {checked: false},
  };

  const settings = collectStockBasicEntityComponentSettings(
    (key) => checked[key],
    {},
  );

  assert.deepEqual(settings, {
    SituationPerception: false,
    SelfPerception: true,
    PersonBySituation: false,
  });
}

testComponentFieldsAreConstrainedToStockQuestionSet();
testMissingComponentSettingsDefaultEnabled();
testToggleHtmlRendersNamedCheckboxes();
testCollectComponentSettingsUsesCheckboxState();
console.log("app_component_controls_test passed");
