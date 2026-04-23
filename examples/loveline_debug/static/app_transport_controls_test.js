const assert = require("assert/strict");
const fs = require("fs");
const path = require("path");

const {
  mountButtonState,
  runOperationButtonState,
  startRunFromCurrentDraft,
} = require("./app.js");

const html = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");

function testNewRunLivesInRunOperationsHeader() {
  const module = html.match(/<div class="band">[\s\S]*?<h2>Run Operations<\/h2>[\s\S]*?<\/div>\s*<div class="row">([\s\S]*?)<\/div>/);
  const header = module[0];
  const controls = module[1];

  assert.match(header, /id="controlNewRun"[^>]*>New Run<\/button>/);
  assert.match(controls, /id="controlPlay"[^>]*>Play<\/button>/);
  assert.match(controls, /id="controlPause"[^>]*>Pause<\/button>/);
  assert.match(controls, /id="controlStep"[^>]*>Step<\/button>/);
  assert.match(controls, /id="controlStop"[^>]*>Stop<\/button>/);
  assert.doesNotMatch(controls, /id="controlNewRun"/);
}

function testMountButtonStateReflectsMountedDraft() {
  assert.deepEqual(mountButtonState({name: "draft"}), {
    mounted: false,
    text: "Mount Draft",
    className: "warn",
    disabled: false,
  });
}

function testRunOperationsStayDisabledUntilMounted() {
  assert.deepEqual(runOperationButtonState(null, false), {
    newRunDisabled: true,
    playDisabled: true,
    pauseDisabled: true,
    stepDisabled: true,
    stopDisabled: true,
  });

  assert.deepEqual(runOperationButtonState({control: {is_paused: true, is_running: false}}, true), {
    newRunDisabled: false,
    playDisabled: false,
    pauseDisabled: true,
    stepDisabled: false,
    stopDisabled: false,
  });
}

async function testStartRunRequiresMountedDraft() {
  await assert.rejects(
    startRunFromCurrentDraft({
      collect() {
        return {name: "current draft"};
      },
      isMounted() {
        return false;
      },
      async apiClient() {
        throw new Error("should not start");
      },
    }),
    /Mount a draft before starting a run/
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
    isMounted() {
      return true;
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
    isMounted() {
      return true;
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
  testNewRunLivesInRunOperationsHeader();
  testMountButtonStateReflectsMountedDraft();
  testRunOperationsStayDisabledUntilMounted();
  await testStartRunRequiresMountedDraft();
  await testStartRunUsesCurrentDraftRunApiAndPausedMessage();
  await testStartRunUsesServerStartPausedTruthForPlayingMessage();
  console.log("app_transport_controls_test passed");
})();
