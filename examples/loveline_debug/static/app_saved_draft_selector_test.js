const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const {
  draftSaveName,
  loadSavedDraftByName,
} = require("./app.js");

const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");

async function testSavedDraftSelectorLoadsChosenDraft() {
  const calls = [];
  let hydrated = false;
  let markedClean = false;
  let message = "";

  const loaded = await loadSavedDraftByName("date night", {
    confirmDiscard(action) {
      calls.push(["confirm", action]);
      return true;
    },
    async apiClient(url) {
      calls.push(["api", url]);
      return {name: "date night", selected_candidate_ids: ["alex_id", "blake_id"]};
    },
    hydrate() {
      hydrated = true;
    },
    markCleanState() {
      markedClean = true;
    },
    showMessage(value) {
      message = value;
    },
  });

  assert.equal(loaded, true);
  assert.deepEqual(calls, [
    ["confirm", "load another saved draft"],
    ["api", "/api/draft?name=date%20night"],
  ]);
  assert.equal(hydrated, true);
  assert.equal(markedClean, true);
  assert.equal(message, "Draft loaded.");
}

async function testSavedDraftSelectorHonorsDiscardCancellation() {
  let apiCalled = false;
  let hydrated = false;

  const loaded = await loadSavedDraftByName("other", {
    confirmDiscard() {
      return false;
    },
    async apiClient() {
      apiCalled = true;
      return {};
    },
    hydrate() {
      hydrated = true;
    },
  });

  assert.equal(loaded, false);
  assert.equal(apiCalled, false);
  assert.equal(hydrated, false);
}

function testSavedDraftHeaderHasNoSeparateLoadButton() {
  const header = html.match(/<header>([\s\S]*?)<\/header>/)[1];

  assert.match(header, /<select id="loadDraft">/);
  assert.match(header, /id="createDraft"/);
  assert.match(header, /id="saveDraft"/);
  assert.doesNotMatch(header, /id="loadDraftBtn"/);
  assert.doesNotMatch(header, /id="draftName"/);
  assert.doesNotMatch(header, /<input[^>]+aria-label="Draft name"/);
}

function testSaveNameComesFromDraftState() {
  assert.equal(draftSaveName({name: "date night"}), "date night");
  assert.equal(draftSaveName({}, "loaded draft"), "loaded draft");
  assert.equal(draftSaveName({}, ""), "two_candidate_debug");
}

(async () => {
  await testSavedDraftSelectorLoadsChosenDraft();
  await testSavedDraftSelectorHonorsDiscardCancellation();
  testSavedDraftHeaderHasNoSeparateLoadButton();
  testSaveNameComesFromDraftState();
  console.log("app_saved_draft_selector_test passed");
})();
