let source = null;
let draft = null;
let activeTab = "contestants";

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {"Content-Type": "application/json"},
    ...options,
  });
  const payload = await response.json();
  if (!response.ok || payload.error) throw new Error(payload.error || response.statusText);
  return payload;
}

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function setMessage(text, isError = false) {
  $("message").textContent = text;
  $("message").className = isError ? "error" : "muted";
}

function hydrateInputs() {
  $("draftName").value = draft.name || "two_candidate_debug";
  $("maxSteps").value = draft.run.max_steps || 8;
  $("disableLm").checked = Boolean(draft.run.disable_language_model);
  $("apiType").value = draft.run.api_type || "openai";
  $("modelName").value = draft.run.model_name || "gpt-4o";
  $("contestantsJson").value = pretty(draft.contestants);
  $("scenesJson").value = pretty({
    scene_defaults: draft.scene_defaults,
    scene_types: draft.scene_types,
    scenes: draft.scenes,
  });
  $("snapshotJson").value = pretty(draft);
  const selected = new Set(draft.selected_candidate_ids || []);
  for (const option of $("maleCandidate").options) option.selected = selected.has(option.value);
  for (const option of $("femaleCandidate").options) option.selected = selected.has(option.value);
  $("candidateTags").innerHTML = draft.contestants.map((item) =>
    `<span class="pill">${item.gender}: ${item.name}</span>`
  ).join("");
}

function collectDraft() {
  if (activeTab === "snapshot") {
    draft = JSON.parse($("snapshotJson").value);
  } else {
    draft.contestants = JSON.parse($("contestantsJson").value);
    const scenesPayload = JSON.parse($("scenesJson").value);
    draft.scene_defaults = scenesPayload.scene_defaults;
    draft.scene_types = scenesPayload.scene_types;
    draft.scenes = scenesPayload.scenes;
  }
  draft.name = $("draftName").value;
  draft.run.max_steps = Number($("maxSteps").value || 8);
  draft.run.disable_language_model = $("disableLm").checked;
  draft.run.api_type = $("apiType").value;
  draft.run.model_name = $("modelName").value;
  return draft;
}

function populateCandidates() {
  $("sourceRoot").textContent = source.starter_root;
  const men = source.candidates.filter((item) => item.gender === "man");
  const women = source.candidates.filter((item) => item.gender === "woman");
  $("maleCandidate").innerHTML = men.map((item) =>
    `<option value="${item.id}">${item.name}</option>`
  ).join("");
  $("femaleCandidate").innerHTML = women.map((item) =>
    `<option value="${item.id}">${item.name}</option>`
  ).join("");
}

async function refreshDrafts() {
  const drafts = await api("/api/drafts");
  $("loadDraft").innerHTML = drafts.map((item) =>
    `<option value="${item.name}">${item.name}</option>`
  ).join("");
}

async function refreshStatus() {
  const payload = await api("/api/status");
  $("status").textContent = pretty(payload.active || {status: "idle"});
  $("recentRuns").innerHTML = payload.recent_runs.map((run) => {
    const id = run.run_id;
    const links = run.artifacts || {};
    const rel = (path) => path ? path.split("/runs/").pop() : null;
    const html = rel(links.html_log);
    const json = rel(links.structured_log);
    const cfg = rel(links.config_snapshot);
    return `<li><strong>${id}</strong> ${run.status || ""}
      ${html ? `<a href="/artifacts/${html}" target="_blank">html</a>` : ""}
      ${json ? `<a href="/artifacts/${json}" target="_blank">json</a>` : ""}
      ${cfg ? `<a href="/artifacts/${cfg}" target="_blank">config</a>` : ""}
    </li>`;
  }).join("");
}

async function init() {
  source = await api("/api/source");
  populateCandidates();
  draft = await api("/api/draft/default");
  hydrateInputs();
  await refreshDrafts();
  await refreshStatus();
  setInterval(refreshStatus, 2000);
}

document.querySelectorAll(".tabs button").forEach((button) => {
  button.addEventListener("click", () => {
    activeTab = button.dataset.tab;
    document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("active"));
    button.classList.add("active");
    $("tabContestants").style.display = activeTab === "contestants" ? "" : "none";
    $("tabScenes").style.display = activeTab === "scenes" ? "" : "none";
    $("tabSnapshot").style.display = activeTab === "snapshot" ? "" : "none";
    try {
      collectDraft();
      hydrateInputs();
    } catch (error) {
      setMessage(error.message, true);
    }
  });
});

$("applySelection").addEventListener("click", async () => {
  try {
    const ids = [$("maleCandidate").value, $("femaleCandidate").value].join(",");
    draft = await api(`/api/draft/selection?ids=${encodeURIComponent(ids)}`);
    hydrateInputs();
    setMessage("Pair applied.");
  } catch (error) {
    setMessage(error.message, true);
  }
});

$("saveDraft").addEventListener("click", async () => {
  try {
    const payload = await api("/api/draft", {
      method: "POST",
      body: JSON.stringify({name: $("draftName").value, draft: collectDraft()}),
    });
    await refreshDrafts();
    hydrateInputs();
    setMessage(`Saved ${payload.path}`);
  } catch (error) {
    setMessage(error.message, true);
  }
});

$("loadDraftBtn").addEventListener("click", async () => {
  try {
    draft = await api(`/api/draft?name=${encodeURIComponent($("loadDraft").value)}`);
    hydrateInputs();
    setMessage("Draft loaded.");
  } catch (error) {
    setMessage(error.message, true);
  }
});

$("runDraft").addEventListener("click", async () => {
  try {
    const record = await api("/api/run", {
      method: "POST",
      body: JSON.stringify({draft: collectDraft()}),
    });
    setMessage(`Started ${record.run_id}. Runs start paused; use Play or Step.`);
    await refreshStatus();
  } catch (error) {
    setMessage(error.message, true);
  }
});

document.querySelectorAll("[data-command]").forEach((button) => {
  button.addEventListener("click", async () => {
    try {
      await api(`/api/control/${button.dataset.command}`, {method: "POST", body: "{}"});
      await refreshStatus();
    } catch (error) {
      setMessage(error.message, true);
    }
  });
});

init().catch((error) => setMessage(error.message, true));

