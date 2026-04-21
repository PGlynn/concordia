let source = null;
let draft = null;
let activeTab = "config";

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

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function setMessage(text, isError = false) {
  $("message").textContent = text;
  $("message").className = isError ? "error" : "muted";
}

function linesFromText(text) {
  return String(text || "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function textFromLines(value) {
  return Array.isArray(value) ? value.join("\n") : String(value || "");
}

function parseJsonField(id, fallback) {
  const element = $(id);
  if (!element) return fallback;
  const text = element.value.trim();
  return text ? JSON.parse(text) : fallback;
}

function selectedNames() {
  return (draft?.contestants || []).map((item) => item.name).filter(Boolean);
}

function renderCandidateOptions(selectId, gender) {
  const selected = new Set(draft.selected_candidate_ids || []);
  const candidates = source.candidates.filter((item) => item.gender === gender);
  $(selectId).innerHTML = candidates.map((item) => {
    const optionSelected = selected.has(item.id) ? " selected" : "";
    return `<option value="${escapeHtml(item.id)}"${optionSelected}>${escapeHtml(item.name)}</option>`;
  }).join("");
}

function renderConfigTab() {
  renderCandidateOptions("maleCandidate", "man");
  renderCandidateOptions("femaleCandidate", "woman");
  $("schemaVersion").value = draft.schema_version ?? "";
  $("createdAt").value = draft.created_at || "";
  $("updatedAt").value = draft.updated_at || "";
  $("sourceRootInput").value = draft.source_root || source.starter_root || "";
  $("mainGameMasterName").value = draft.scene_defaults?.main_game_master_name || "Show Runner";
  $("defaultPremise").value = draft.scene_defaults?.default_premise || "";
  $("maxSteps").value = draft.run?.max_steps || 8;
  $("disableLm").checked = Boolean(draft.run?.disable_language_model);
  $("apiType").value = draft.run?.api_type || "openai";
  $("modelName").value = draft.run?.model_name || "gpt-4o";
  $("checkpointEveryStep").checked = draft.run?.checkpoint_every_step !== false;
  $("configRawJson").value = pretty({
    schema_version: draft.schema_version,
    name: draft.name,
    created_at: draft.created_at,
    updated_at: draft.updated_at,
    source_root: draft.source_root,
    selected_candidate_ids: draft.selected_candidate_ids,
    run: draft.run,
    scene_defaults: draft.scene_defaults,
  });
  $("candidateTags").innerHTML = (draft.contestants || []).map((item) =>
    `<span class="pill">${escapeHtml(item.gender)}: ${escapeHtml(item.name)}</span>`
  ).join("");
}

function renderCandidatesTab() {
  $("candidateEditor").innerHTML = (draft.contestants || []).map((candidate, index) => {
    const params = candidate.entity_params || {};
    return `<article class="editor-block" data-candidate-index="${index}">
      <div class="block-title">
        <h3>${escapeHtml(candidate.name || `Candidate ${index + 1}`)}</h3>
        <span class="pill">${escapeHtml(candidate.gender || "candidate")}</span>
      </div>
      <div class="grid two">
        <label>Name<input data-candidate-field="name" value="${escapeHtml(candidate.name)}"></label>
        <label>Gender<input data-candidate-field="gender" value="${escapeHtml(candidate.gender)}"></label>
        <label>ID<input data-candidate-field="id" value="${escapeHtml(candidate.id)}"></label>
        <label>Prefab<input data-candidate-field="prefab" value="${escapeHtml(candidate.prefab || "basic__Entity")}"></label>
      </div>
      <label>Entity Goal<textarea data-candidate-field="goal">${escapeHtml(params.goal || "")}</textarea></label>
      <label class="checkline"><input data-candidate-field="prefix_entity_name" type="checkbox" ${params.prefix_entity_name ? "checked" : ""}> Prefix entity name</label>
      <label>Player Context<textarea class="tall" data-candidate-field="player_specific_context">${escapeHtml(candidate.player_specific_context || "")}</textarea></label>
      <label>Player Memories<textarea data-candidate-field="player_specific_memories">${escapeHtml(textFromLines(candidate.player_specific_memories))}</textarea></label>
      <label>Debug Tags<textarea data-candidate-field="derived_debug_tags">${escapeHtml(textFromLines(candidate.derived_debug_tags))}</textarea></label>
      <details>
        <summary>Exact candidate JSON</summary>
        <textarea class="json-box" id="candidateRaw${index}">${escapeHtml(pretty(candidate))}</textarea>
      </details>
    </article>`;
  }).join("");
  $("contestantsJson").value = pretty(draft.contestants || []);
}

function sceneTypeOptions(selectedType) {
  return Object.keys(draft.scene_types || {}).map((name) => {
    const selected = name === selectedType ? " selected" : "";
    return `<option value="${escapeHtml(name)}"${selected}>${escapeHtml(name)}</option>`;
  }).join("");
}

function renderSceneTypeEditor() {
  $("sceneTypeEditor").innerHTML = Object.entries(draft.scene_types || {}).map(([name, cfg], index) =>
    `<article class="editor-block compact" data-scene-type="${escapeHtml(name)}">
      <div class="block-title">
        <h3>${escapeHtml(name)}</h3>
        <button class="secondary small" data-remove-type="${escapeHtml(name)}">Remove</button>
      </div>
      <div class="grid type-grid">
        <label>Type Key<input data-scene-type-field="name" value="${escapeHtml(name)}"></label>
        <label>Rounds<input type="number" min="1" data-scene-type-field="rounds" value="${escapeHtml(cfg.rounds || 1)}"></label>
      </div>
      <label>Call to Action<textarea data-scene-type-field="call_to_action">${escapeHtml(cfg.call_to_action || "")}</textarea></label>
      <details>
        <summary>Exact scene type JSON</summary>
        <textarea class="json-box" id="sceneTypeRaw${index}">${escapeHtml(pretty(cfg))}</textarea>
      </details>
    </article>`
  ).join("");
}

function renderSceneEditor() {
  const names = selectedNames();
  $("sceneListEditor").innerHTML = (draft.scenes || []).map((scene, index) => {
    const premise = scene.premise || {};
    const participantChecks = names.map((name) => {
      const checked = (scene.participants || []).includes(name) ? " checked" : "";
      return `<label class="checkline"><input type="checkbox" data-scene-participant="${escapeHtml(name)}"${checked}> ${escapeHtml(name)}</label>`;
    }).join("");
    const premiseFields = names.map((name) =>
      `<label>${escapeHtml(name)} Premise<textarea data-scene-premise="${escapeHtml(name)}">${escapeHtml(textFromLines(premise[name]))}</textarea></label>`
    ).join("");
    return `<article class="editor-block" data-scene-index="${index}">
      <div class="block-title">
        <h3>${escapeHtml(scene.id || `Scene ${index + 1}`)}</h3>
        <button class="secondary small" data-remove-scene="${index}">Remove</button>
      </div>
      <div class="grid scene-grid">
        <label>Scene ID<input data-scene-field="id" value="${escapeHtml(scene.id || "")}"></label>
        <label>Type<select data-scene-field="type">${sceneTypeOptions(scene.type)}</select></label>
        <label>Rounds Override<input type="number" min="" data-scene-field="num_rounds" value="${escapeHtml(scene.num_rounds || "")}" placeholder="type default"></label>
      </div>
      <div class="field-label">Participants</div>
      <div class="checkbox-row">${participantChecks}</div>
      ${premiseFields}
      <details>
        <summary>Exact scene JSON</summary>
        <textarea class="json-box" id="sceneRaw${index}">${escapeHtml(pretty(scene))}</textarea>
      </details>
    </article>`;
  }).join("");
}

function renderScenesTab() {
  $("sceneDefaultsMainGameMaster").value = draft.scene_defaults?.main_game_master_name || "Show Runner";
  $("sceneDefaultsPremise").value = draft.scene_defaults?.default_premise || "";
  renderSceneTypeEditor();
  renderSceneEditor();
  $("scenesJson").value = pretty({
    scene_defaults: draft.scene_defaults,
    scene_types: draft.scene_types,
    scenes: draft.scenes,
  });
}

function hydrateInputs() {
  $("draftName").value = draft.name || "two_candidate_debug";
  $("sourceRoot").textContent = source.starter_root;
  renderConfigTab();
  renderCandidatesTab();
  renderScenesTab();
  $("snapshotJson").value = pretty(draft);
}

function collectConfigForm() {
  const raw = parseJsonField("configRawJson", {});
  draft.schema_version = Number($("schemaVersion").value || raw.schema_version || 1);
  draft.created_at = $("createdAt").value || raw.created_at;
  draft.updated_at = $("updatedAt").value || raw.updated_at;
  draft.source_root = $("sourceRootInput").value || raw.source_root || source.starter_root;
  draft.selected_candidate_ids = [$("maleCandidate").value, $("femaleCandidate").value];
  draft.scene_defaults = {
    ...(raw.scene_defaults || draft.scene_defaults || {}),
    main_game_master_name: $("mainGameMasterName").value || "Show Runner",
    default_premise: $("defaultPremise").value,
  };
  draft.run = {
    ...(raw.run || draft.run || {}),
    max_steps: Number($("maxSteps").value || 8),
    disable_language_model: $("disableLm").checked,
    api_type: $("apiType").value,
    model_name: $("modelName").value,
    checkpoint_every_step: $("checkpointEveryStep").checked,
  };
}

function collectCandidateForms() {
  const blocks = [...document.querySelectorAll("[data-candidate-index]")];
  if (!blocks.length) return;
  draft.contestants = blocks.map((block) => {
    const index = Number(block.dataset.candidateIndex);
    const raw = parseJsonField(`candidateRaw${index}`, draft.contestants[index] || {});
    const field = (name) => block.querySelector(`[data-candidate-field="${name}"]`);
    const name = field("name").value;
    const candidate = {
      ...raw,
      id: field("id").value,
      name,
      gender: field("gender").value,
      prefab: field("prefab").value || "basic__Entity",
      entity_params: {
        ...(raw.entity_params || {}),
        name,
        goal: field("goal").value,
        prefix_entity_name: field("prefix_entity_name").checked,
      },
      player_specific_context: field("player_specific_context").value,
      player_specific_memories: linesFromText(field("player_specific_memories").value),
      derived_debug_tags: linesFromText(field("derived_debug_tags").value),
    };
    return candidate;
  });
}

function collectSceneTypeForms() {
  const entries = [...document.querySelectorAll("[data-scene-type]")];
  if (!entries.length) return;
  const next = {};
  entries.forEach((block, index) => {
    const oldName = block.dataset.sceneType;
    const raw = parseJsonField(`sceneTypeRaw${index}`, draft.scene_types[oldName] || {});
    const name = block.querySelector('[data-scene-type-field="name"]').value.trim();
    if (!name) return;
    next[name] = {
      ...raw,
      rounds: Number(block.querySelector('[data-scene-type-field="rounds"]').value || 1),
      call_to_action: block.querySelector('[data-scene-type-field="call_to_action"]').value,
    };
  });
  draft.scene_types = next;
}

function collectSceneForms() {
  const blocks = [...document.querySelectorAll("[data-scene-index]")];
  if (!blocks.length) return;
  draft.scenes = blocks.map((block) => {
    const index = Number(block.dataset.sceneIndex);
    const raw = parseJsonField(`sceneRaw${index}`, draft.scenes[index] || {});
    const roundsValue = block.querySelector('[data-scene-field="num_rounds"]').value;
    const participants = [...block.querySelectorAll("[data-scene-participant]:checked")]
      .map((input) => input.dataset.sceneParticipant);
    const premise = {};
    block.querySelectorAll("[data-scene-premise]").forEach((textarea) => {
      const lines = linesFromText(textarea.value);
      if (lines.length) premise[textarea.dataset.scenePremise] = lines;
    });
    const scene = {
      ...raw,
      id: block.querySelector('[data-scene-field="id"]').value,
      type: block.querySelector('[data-scene-field="type"]').value,
      participants,
      premise,
    };
    if (roundsValue) scene.num_rounds = Number(roundsValue);
    else delete scene.num_rounds;
    return scene;
  });
}

function collectScenesForms() {
  if (activeTab !== "scenes") {
    return;
  }
  draft.scene_defaults = {
    ...(draft.scene_defaults || {}),
    main_game_master_name: $("sceneDefaultsMainGameMaster").value || "Show Runner",
    default_premise: $("sceneDefaultsPremise").value,
  };
  collectSceneTypeForms();
  collectSceneForms();
}

function collectDraft() {
  if (activeTab === "snapshot") {
    draft = JSON.parse($("snapshotJson").value);
  } else {
    collectConfigForm();
    collectCandidateForms();
    collectScenesForms();
  }
  draft.name = $("draftName").value;
  $("snapshotJson").value = pretty(draft);
  return draft;
}

function populateChrome() {
  $("sourceRoot").textContent = source.starter_root;
}

async function refreshDrafts() {
  const drafts = await api("/api/drafts");
  $("loadDraft").innerHTML = drafts.map((item) =>
    `<option value="${escapeHtml(item.name)}">${escapeHtml(item.name)}</option>`
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
    return `<li><strong>${escapeHtml(id)}</strong> ${escapeHtml(run.status || "")}
      ${html ? `<a href="/artifacts/${escapeHtml(html)}" target="_blank">html</a>` : ""}
      ${json ? `<a href="/artifacts/${escapeHtml(json)}" target="_blank">json</a>` : ""}
      ${cfg ? `<a href="/artifacts/${escapeHtml(cfg)}" target="_blank">config</a>` : ""}
    </li>`;
  }).join("");
}

async function init() {
  source = await api("/api/source");
  populateChrome();
  draft = await api("/api/draft/default");
  hydrateInputs();
  await refreshDrafts();
  await refreshStatus();
  setInterval(refreshStatus, 2000);
}

document.querySelectorAll(".tabs button").forEach((button) => {
  button.addEventListener("click", () => {
    try {
      collectDraft();
      activeTab = button.dataset.tab;
      document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("active"));
      button.classList.add("active");
      document.querySelectorAll("[data-tab-panel]").forEach((panel) => {
        panel.style.display = panel.dataset.tabPanel === activeTab ? "" : "none";
      });
      hydrateInputs();
      setMessage("");
    } catch (error) {
      setMessage(error.message, true);
    }
  });
});

$("applySelection").addEventListener("click", async () => {
  try {
    const ids = [$("maleCandidate").value, $("femaleCandidate").value].join(",");
    draft = await api(`/api/draft/selection?ids=${encodeURIComponent(ids)}`);
    draft.name = $("draftName").value || draft.name;
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

$("applyConfigJson").addEventListener("click", () => {
  try {
    const raw = JSON.parse($("configRawJson").value);
    draft = {
      ...draft,
      schema_version: raw.schema_version ?? draft.schema_version,
      name: raw.name || draft.name,
      created_at: raw.created_at ?? draft.created_at,
      updated_at: raw.updated_at ?? draft.updated_at,
      source_root: raw.source_root ?? draft.source_root,
      selected_candidate_ids: raw.selected_candidate_ids ?? draft.selected_candidate_ids,
      run: raw.run ?? draft.run,
      scene_defaults: raw.scene_defaults ?? draft.scene_defaults,
    };
    hydrateInputs();
    setMessage("Config JSON applied.");
  } catch (error) {
    setMessage(error.message, true);
  }
});

$("applyContestantsJson").addEventListener("click", () => {
  try {
    draft.contestants = JSON.parse($("contestantsJson").value);
    hydrateInputs();
    setMessage("Candidates JSON applied.");
  } catch (error) {
    setMessage(error.message, true);
  }
});

$("applyScenesJson").addEventListener("click", () => {
  try {
    const raw = JSON.parse($("scenesJson").value);
    draft.scene_defaults = raw.scene_defaults;
    draft.scene_types = raw.scene_types;
    draft.scenes = raw.scenes;
    hydrateInputs();
    setMessage("Scenes JSON applied.");
  } catch (error) {
    setMessage(error.message, true);
  }
});

$("addSceneType").addEventListener("click", () => {
  try {
    collectDraft();
    let index = Object.keys(draft.scene_types || {}).length + 1;
    let name = `scene_type_${index}`;
    while (draft.scene_types[name]) name = `scene_type_${++index}`;
    draft.scene_types[name] = {rounds: 1, call_to_action: ""};
    hydrateInputs();
  } catch (error) {
    setMessage(error.message, true);
  }
});

$("addScene").addEventListener("click", () => {
  try {
    collectDraft();
    const names = selectedNames();
    const type = Object.keys(draft.scene_types || {})[0] || "pod_date";
    draft.scenes.push({
      id: `scene_${draft.scenes.length + 1}`,
      type,
      participants: names,
      premise: Object.fromEntries(names.map((name) => [name, []])),
    });
    hydrateInputs();
  } catch (error) {
    setMessage(error.message, true);
  }
});

document.addEventListener("click", (event) => {
  const removeType = event.target.closest("[data-remove-type]");
  const removeScene = event.target.closest("[data-remove-scene]");
  if (!removeType && !removeScene) return;
  try {
    collectDraft();
    if (removeType) delete draft.scene_types[removeType.dataset.removeType];
    if (removeScene) draft.scenes.splice(Number(removeScene.dataset.removeScene), 1);
    hydrateInputs();
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
