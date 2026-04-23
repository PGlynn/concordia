const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const {
  startRunFromCurrentDraft,
} = require("./app.js");

const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");

function testNewRunLivesBesideTransportControls() {
  const controls = html.match(/<div class="row" style="margin-top:8px">([\s\S]*?)<\/div>/)[1];

  assert.match(controls, /id="controlNewRun"[^>]*>New Run<\/button>/);
  assert.match(controls, /id="controlPlay"[^>]*>Play<\/button>/);
  assert.match(controls, /id="controlPause"[^>]*>Pause<\/button>/);
  assert.match(controls, /id="controlStep"[^>]*>Step<\/button>/);
  assert.match(controls, /id="controlStop"[^>]*>Stop<\/button>/);
  assert.ok(controls.indexOf('id="controlNewRun"') < controls.indexOf('id="controlPlay"'));
  assert.doesNotMatch(
    controls.match(/<button id="controlNewRun"[\s\S]*?<\/button>/)[0],
    /data-command=/
  );
}

async function testStartRunUsesCurrentDraftRunApiAndPausedMessage() {
  const calls = [];
  let message = "";
  let refreshed = false;
  let conversationSelected = false;
  let activeRunSelected = false;
  let dialogueRendered = false;

  const record = await startRunFromCurrentDraft({
    async apiClient(url, options) {
      calls.push([url, options]);
      return {run_id: "run_new", start_paused: true};
    },
    collect() {
      return {name: "current draft"};
    },
    showMessage(value) {
      message = value;
    },
    async refresh() {
      refreshed = true;
    },
    selectConversationTab() {
      conversationSelected = true;
    },
    selectActiveDialogueRun() {
      activeRunSelected = true;
    },
    renderDialogue() {
      dialogueRendered = true;
    },
  });

  assert.deepEqual(record, {run_id: "run_new", start_paused: true});
  assert.equal(calls[0][0], "/api/run");
  assert.equal(calls[0][1].method, "POST");
  assert.deepEqual(JSON.parse(calls[0][1].body), {draft: {name: "current draft"}});
  assert.equal(message, "Started run_new paused.");
  assert.equal(refreshed, true);
  assert.equal(conversationSelected, true);
  assert.equal(activeRunSelected, true);
  assert.equal(dialogueRendered, true);
}

async function testStartRunUsesServerStartPausedTruthForPlayingMessage() {
  let message = "";

  await startRunFromCurrentDraft({
    async apiClient() {
      return {run_id: "run_live", start_paused: false};
    },
    collect() {
      return {};
    },
    showMessage(value) {
      message = value;
    },
    async refresh() {},
    selectConversationTab() {},
    selectActiveDialogueRun() {},
    renderDialogue() {},
  });

  assert.equal(message, "Started run_live playing.");
}

(async () => {
  testNewRunLivesBesideTransportControls();
  await testStartRunUsesCurrentDraftRunApiAndPausedMessage();
  await testStartRunUsesServerStartPausedTruthForPlayingMessage();
  console.log("app_transport_controls_test passed");
})();
