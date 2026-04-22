let source = null;
let draft = null;
let activeTab = "config";
let latestStatus = null;
let inspectorState = null;
let compareState = null;
let logsState = null;
let cleanDraftJson = "";
let isDirty = false;

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

function draftFingerprint(value) {
  return JSON.stringify(value ?? null, (_key, item) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return item;
    return Object.keys(item).sort().reduce((result, key) => {
      result[key] = item[key];
      return result;
    }, {});
  });
}

function summarizeDraftContext(value) {
  const run = value?.run || {};
  const contestants = value?.contestants || [];
  return {
    selected_pair: contestants.map((item) => item.name).filter(Boolean),
    selected_candidate_ids: value?.selected_candidate_ids || [],
    max_steps: run.max_steps,
    disable_language_model: Boolean(run.disable_language_model),
    api_type: run.api_type,
    model_name: run.model_name,
    start_paused: run.start_paused !== false,
    checkpoint_every_step: run.checkpoint_every_step !== false,
    scene_count: (value?.scenes || []).length,
    source_root: value?.source_root,
  };
}

function runContextLabel(context) {
  const pair = (context?.selected_pair || context?.candidates || []).filter(Boolean).join(" vs ");
  const lm = context?.disable_language_model ? "LM disabled" : (context?.model_name || context?.model || "LM enabled");
  return [
    pair,
    context?.max_steps ? `${context.max_steps} steps` : "",
    lm,
    context?.start_paused === false ? "starts playing" : "starts paused",
    context?.checkpoint_every_step === false ? "no checkpoints" : "checkpoints",
  ].filter(Boolean).join(" | ");
}

function displayValue(value) {
  if (Array.isArray(value)) return value.join("\n");
  if (value && typeof value === "object") return pretty(value);
  return String(value ?? "");
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

function updateDirtyIndicator() {
  const element = $("dirtyState");
  if (!element) return;
  element.textContent = isDirty ? "Unsaved changes" : "No unsaved changes";
  element.className = isDirty ? "dirty" : "muted";
}

function markClean() {
  cleanDraftJson = draftFingerprint(draft);
  isDirty = false;
  updateDirtyIndicator();
}

function markDirty() {
  if (!cleanDraftJson) cleanDraftJson = draftFingerprint(draft);
  isDirty = true;
  updateDirtyIndicator();
}

function refreshDirtyState() {
  isDirty = Boolean(cleanDraftJson) && draftFingerprint(draft) !== cleanDraftJson;
  updateDirtyIndicator();
  return isDirty;
}

function confirmDiscardChanges(action) {
  if (!isDirty) return true;
  return window.confirm(`Unsaved changes may be replaced. Continue and ${action}?`);
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

function uniqueLines(...values) {
  const result = [];
  values.flat().forEach((value) => {
    if (value && !result.includes(value)) result.push(value);
  });
  return result;
}

function remapName(value, nameMap) {
  return nameMap.get(value) || value;
}

function remapSceneForSelection(scene, nameMap, selectedNamesSet) {
  const next = {...scene};
  next.participants = (scene.participants || [])
    .map((name) => remapName(name, nameMap))
    .filter((name, index, names) => selectedNamesSet.has(name) && names.indexOf(name) === index);
  const premise = {};
  Object.entries(scene.premise || {}).forEach(([name, lines]) => {
    const nextName = remapName(name, nameMap);
    if (!selectedNamesSet.has(nextName)) return;
    premise[nextName] = uniqueLines(premise[nextName] || [], Array.isArray(lines) ? lines : [String(lines)]);
  });
  next.premise = premise;
  return next;
}

function mergeSelectionDraft(currentDraft, selectionDraft) {
  const currentById = new Map((currentDraft.contestants || []).map((item) => [item.id, item]));
  const currentByGender = new Map((currentDraft.contestants || []).map((item) => [item.gender, item]));
  const nextContestants = (selectionDraft.contestants || []).map((candidate) => {
    const edited = currentById.get(candidate.id);
    return edited ? {...candidate, ...edited} : candidate;
  });
  const nextByGender = new Map(nextContestants.map((item) => [item.gender, item]));
  const nameMap = new Map();
  currentByGender.forEach((oldCandidate, gender) => {
    const nextCandidate = nextByGender.get(gender);
    if (oldCandidate?.name && nextCandidate?.name) {
      nameMap.set(oldCandidate.name, nextCandidate.name);
    }
  });
  const selectedNamesSet = new Set(nextContestants.map((item) => item.name).filter(Boolean));
  const currentScenes = currentDraft.scenes || [];
  const nextScenes = currentScenes.length
    ? currentScenes.map((scene) => remapSceneForSelection(scene, nameMap, selectedNamesSet))
    : (selectionDraft.scenes || []);
  return {
    ...selectionDraft,
    ...currentDraft,
    selected_candidate_ids: selectionDraft.selected_candidate_ids,
    contestants: nextContestants,
    scenes: nextScenes,
  };
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
  $("startPaused").checked = draft.run?.start_paused !== false;
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
    start_paused: $("startPaused").checked,
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
  latestStatus = payload;
  renderRunSummary(payload);
  updateControlButtons(payload);
  $("status").textContent = pretty({
    active: payload.active || {status: "idle"},
    control: payload.control || null,
  });
  renderRecentRuns(payload.recent_runs || []);
  if (!inspectorState && (payload.recent_runs || []).length) {
    const run = payload.recent_runs.find((item) => item.artifacts?.structured_log);
    if (run) loadInspector(run.run_id).catch((error) => setInspectorMessage(error.message, true));
  }
}

function displayRunState(payload) {
  const active = payload.active;
  if (!active) return "idle";
  if (payload.control?.state) return payload.control.state;
  return active.status || "unknown";
}

function renderRunSummary(payload) {
  const active = payload.active;
  const context = active?.summary || active?.run_context;
  const rows = active
    ? [
        ["Run", active.run_id],
        ["Lifecycle", active.status],
        ["Control", displayRunState(payload)],
        ["Step", payload.control?.current_step ?? active.current_step ?? 0],
        ["Launch", active.start_paused ? "started paused" : "started playing"],
        ["Pair", (context?.selected_pair || context?.candidates || []).filter(Boolean).join(" vs ")],
        ["Settings", runContextLabel(context)],
      ]
    : [["Run", "none"], ["Lifecycle", "idle"], ["Control", "idle"], ["Step", "0"]];
  $("runSummary").innerHTML = rows.map(([key, value]) =>
    `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd>`
  ).join("");
}

function updateControlButtons(payload = latestStatus) {
  const hasControl = Boolean(payload?.control);
  const isPaused = Boolean(payload?.control?.is_paused);
  const isRunning = Boolean(payload?.control?.is_running);
  $("controlPlay").disabled = !hasControl || isRunning;
  $("controlPause").disabled = !hasControl || isPaused;
  $("controlStep").disabled = !hasControl || !isPaused;
  $("controlStop").disabled = !hasControl;
}

function setInspectorMessage(text, isError = false) {
  $("inspectorMessage").textContent = text;
  $("inspectorMessage").className = isError ? "error" : "muted";
}

function setCompareMessage(text, isError = false) {
  $("compareMessage").textContent = text;
  $("compareMessage").className = isError ? "error" : "muted";
}

function setLogMessage(text, isError = false) {
  $("logMessage").textContent = text;
  $("logMessage").className = isError ? "error" : "muted";
}

function artifactRel(path) {
  return path ? path.split("/runs/").pop() : null;
}

function renderRecentRuns(runs) {
  if (!runs.length) {
    $("recentRuns").innerHTML = '<li class="muted">No runs yet.</li>';
    renderCompareOptions(runs);
    renderLogRunOptions(runs);
    return;
  }
  $("recentRuns").innerHTML = runs.map((run) => {
    const id = run.run_id;
    const links = run.artifacts || {};
    const html = artifactRel(links.html_log);
    const json = artifactRel(links.structured_log);
    const cfg = artifactRel(links.config_snapshot);
    const summary = run.summary || run.run_context || {};
    const meta = [
      run.status || "unknown",
      run.finished_at || run.started_at || summary.snapshot_at || "",
      runContextLabel(summary),
    ].filter(Boolean).join(" | ");
    return `<li class="run-item">
      <div><strong>${escapeHtml(id)}</strong><div class="muted">${escapeHtml(meta)}</div></div>
      <div class="run-actions">
        <button class="secondary small" data-inspect-run="${escapeHtml(id)}" type="button">Inspect</button>
        <button class="secondary small" data-log-run="${escapeHtml(id)}" type="button">Log</button>
        <button class="secondary small" data-compare-left="${escapeHtml(id)}" type="button">Left</button>
        <button class="secondary small" data-compare-right="${escapeHtml(id)}" type="button">Right</button>
        ${html ? `<a href="/artifacts/${escapeHtml(html)}" target="_blank">html</a>` : ""}
        ${json ? `<a href="/artifacts/${escapeHtml(json)}" target="_blank">json</a>` : ""}
        ${cfg ? `<a href="/artifacts/${escapeHtml(cfg)}" target="_blank">config</a>` : ""}
      </div>
    </li>`;
  }).join("");
  renderCompareOptions(runs);
  renderLogRunOptions(runs);
}

function renderCompareOptions(runs) {
  const options = runs.map((run) =>
    `<option value="${escapeHtml(run.run_id)}">${escapeHtml(run.run_id)}</option>`
  ).join("");
  const previousLeft = $("compareLeft").value;
  const previousRight = $("compareRight").value;
  $("compareLeft").innerHTML = options;
  $("compareRight").innerHTML = options;
  if (runs.some((run) => run.run_id === previousLeft)) $("compareLeft").value = previousLeft;
  if (runs.some((run) => run.run_id === previousRight)) $("compareRight").value = previousRight;
  if (!$("compareLeft").value && runs[0]) $("compareLeft").value = runs[0].run_id;
  if ((!$("compareRight").value || $("compareRight").value === $("compareLeft").value) && runs[1]) {
    $("compareRight").value = runs[1].run_id;
  }
}

function renderLogRunOptions(runs) {
  const select = $("logRunSelect");
  if (!select) return;
  const previous = select.value;
  const logRuns = runs.filter((run) => run.artifacts?.structured_log);
  const options = (logRuns.length ? logRuns : runs).map((run) =>
    `<option value="${escapeHtml(run.run_id)}">${escapeHtml(run.run_id)}</option>`
  ).join("");
  select.innerHTML = options;
  if ((logRuns.length ? logRuns : runs).some((run) => run.run_id === previous)) {
    select.value = previous;
  }
}

async function loadInspector(runId, selection = {}) {
  let path = `/api/inspect/${encodeURIComponent(runId)}`;
  if (selection.step !== undefined) {
    const params = new URLSearchParams({step: String(selection.step)});
    if (selection.entity_name) params.set("entity", selection.entity_name);
    if (selection.index !== undefined) params.set("index", String(selection.index));
    path += `?${params.toString()}`;
  }
  inspectorState = await api(path);
  renderInspector();
}

function renderInspector() {
  if (!inspectorState) return;
  const selected = inspectorState.selected;
  $("inspectorRunId").textContent = inspectorState.run_id || "";
  $("inspectorRunInput").value = inspectorState.run_id || $("inspectorRunInput").value;
  $("turnSelect").innerHTML = (inspectorState.entries || []).map((entry) => {
    const isSelected = selected && entry.index === selected.index ? " selected" : "";
    const action = displayValue(entry.action || entry.summary).replace(/\s+/g, " ").trim();
    const label = `Step ${entry.step} - ${entry.entity_name}${action ? ` - ${action.slice(0, 80)}` : ""}`;
    return `<option value="${escapeHtml(entry.index)}"${isSelected}>${escapeHtml(label)}</option>`;
  }).join("");
  if (!inspectorState.available) {
    setInspectorMessage(inspectorState.error || "No structured log is available.", true);
    $("turnInspector").innerHTML = "";
    return;
  }
  setInspectorMessage("");
  if (!selected) {
    $("turnInspector").innerHTML = '<div class="muted">No inspectable entries in this run.</div>';
    return;
  }
  $("turnInspector").innerHTML = renderTurnDetail(selected);
}

async function loadLog(runId) {
  if (!runId) throw new Error("Choose a run.");
  logsState = await api(`/api/logs/${encodeURIComponent(runId)}`);
  renderLogBrowser();
}

function logSearchText(entry) {
  return [
    entry.index,
    entry.step,
    entry.timestamp,
    entry.entity_name,
    entry.component_name,
    entry.entry_type,
    entry.summary,
    entry.preview,
    entry.raw_utterance_text,
    entry.concordia_event_text,
    displayValue(entry.raw_entry),
  ].join(" ").toLowerCase();
}

function filteredLogEntries(
  state = logsState,
  filterText = $("logFilter")?.value || ""
) {
  const entries = state?.entries || [];
  const query = filterText.trim().toLowerCase();
  if (!query) return entries;
  return entries.filter((entry) => logSearchText(entry).includes(query));
}

function renderLogBrowser(state = logsState) {
  if (!state) {
    $("logEntries").innerHTML = '<div class="muted">Choose a run to load its saved structured log.</div>';
    $("logDetails").textContent = "No entry selected.";
    return;
  }
  if (!state.available) {
    setLogMessage(state.error || "No structured log is available.", true);
    $("logEntries").innerHTML = "";
    $("logDetails").textContent = "No entry selected.";
    renderLogArtifactLink(state);
    return;
  }
  const entries = filteredLogEntries(state);
  let selectedIndex = state.selected_index ?? entries[0]?.index;
  if (!entries.some((entry) => entry.index === selectedIndex)) {
    selectedIndex = entries[0]?.index;
  }
  if (state.selected_index === undefined && selectedIndex !== undefined) {
    state.selected_index = selectedIndex;
  }
  setLogMessage(
    `${entries.length} of ${state.entry_count ?? state.entries.length} entries shown.`
  );
  renderLogArtifactLink(state);
  if (!entries.length) {
    $("logEntries").innerHTML = '<div class="muted">No entries match the filter.</div>';
    $("logDetails").textContent = "No entry selected.";
    return;
  }
  $("logEntries").innerHTML = `<table class="log-table">
    <thead><tr><th>#</th><th>Step</th><th>Type</th><th>Entity</th><th>Component</th><th>Summary</th></tr></thead>
    <tbody>${entries.map((entry) => {
      const selected = entry.index === selectedIndex ? " selected" : "";
      return `<tr class="${selected}" data-log-entry="${escapeHtml(entry.index)}">
        <td>${escapeHtml(entry.index)}</td>
        <td>${escapeHtml(entry.step)}</td>
        <td>${escapeHtml(entry.entry_type)}</td>
        <td>${escapeHtml(entry.entity_name)}</td>
        <td>${escapeHtml(entry.component_name)}</td>
        <td class="log-summary"><strong>${escapeHtml(entry.summary || "")}</strong>${renderLogTextSurfacePreview(entry)}</td>
      </tr>`;
    }).join("")}</tbody>
  </table>`;
  const selected = state.entries.find((entry) => entry.index === selectedIndex) || entries[0];
  $("logDetails").textContent = formatLogDetails(selected);
}

function renderLogTextSurfacePreview(entry) {
  const rows = [];
  if (entry.raw_utterance_text) {
    rows.push(`<span class="muted">Raw utterance:</span> ${escapeHtml(entry.raw_utterance_text)}`);
  }
  if (entry.concordia_event_text) {
    rows.push(`<span class="muted">Concordia event/display:</span> ${escapeHtml(entry.concordia_event_text)}`);
  }
  if (!rows.length && entry.preview) {
    rows.push(`<span class="muted">${escapeHtml(entry.preview)}</span>`);
  }
  return rows.length ? `<br>${rows.join("<br>")}` : "";
}

function formatLogDetails(entry) {
  if (!entry) return "No entry selected.";
  const sections = [];
  if (entry.raw_utterance_text) {
    sections.push(`Raw utterance text:\n${entry.raw_utterance_text}`);
  }
  if (entry.concordia_event_text) {
    sections.push(`Concordia event/display text:\n${entry.concordia_event_text}`);
  }
  sections.push(`Raw structured entry:\n${pretty(entry.raw_entry || entry)}`);
  return sections.join("\n\n");
}

function renderLogArtifactLink(state = logsState) {
  const html = artifactRel(state?.artifacts?.html_log);
  const json = artifactRel(state?.artifacts?.structured_log);
  $("logArtifactLink").innerHTML = [
    html ? `<a href="/artifacts/${escapeHtml(html)}" target="_blank">Open saved HTML log viewer</a>` : "",
    json ? `<a href="/artifacts/${escapeHtml(json)}" target="_blank">Open structured_log.json</a>` : "",
  ].filter(Boolean).join(" | ");
}

function renderTextBlock(title, value) {
  const text = displayValue(value).trim();
  if (!text) return "";
  return `<div class="inspector-block"><h3>${escapeHtml(title)}</h3><pre>${escapeHtml(text)}</pre></div>`;
}

function renderUtteranceTextSurfaces(value) {
  const raw = value?.raw_utterance_text;
  const eventText = value?.concordia_event_text;
  if (!raw && !eventText) return renderTextBlock("Action", value?.action);
  return [
    renderTextBlock("Raw Utterance Text", raw),
    renderTextBlock("Concordia Event / Display Text", eventText),
  ].join("");
}

function renderListBlock(title, values) {
  if (!values || !values.length) return "";
  return `<div class="inspector-block"><h3>${escapeHtml(title)}</h3><ul>${values.map((value) =>
    `<li>${escapeHtml(displayValue(value))}</li>`
  ).join("")}</ul></div>`;
}

function renderComponentRows(components) {
  if (!components || !components.length) return "";
  return `<div class="inspector-block"><h3>Component Outputs</h3>${components.map((item) =>
    `<details open><summary>${escapeHtml(item.name)}</summary><pre>${escapeHtml(displayValue(item.value))}</pre></details>`
  ).join("")}</div>`;
}

function renderGmEntries(entries) {
  if (!entries || !entries.length) return "";
  return `<div class="inspector-block"><h3>GM Reaction / Context</h3>${entries.map((entry) =>
    `<details open><summary>${escapeHtml(entry.entity_name || "GM")} ${escapeHtml(entry.summary || "")}</summary><pre>${escapeHtml(displayValue(entry.data))}</pre></details>`
  ).join("")}</div>`;
}

function renderTurnDetail(turn, state = inspectorState) {
  const meta = [
    ["Run", state?.run_id || ""],
    ["Step", turn.step],
    ["Entity", turn.entity_name],
    ["Summary", turn.summary],
  ];
  return `<div class="status-grid compact">${meta.map(([key, value]) =>
    `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd>`
  ).join("")}</div>
  ${renderUtteranceTextSurfaces(turn)}
  ${renderTextBlock("Action Prompt", turn.action_prompt)}
  ${renderListBlock("Observations", turn.observations)}
  ${renderComponentRows(turn.components)}
  ${renderListBlock("Entity Memories", turn.entity_memories)}
  ${renderGmEntries(turn.game_master_entries)}
  ${renderListBlock("Game Master Memories", turn.game_master_memories)}
  <details><summary>Raw Entry</summary><pre>${escapeHtml(displayValue(turn.raw_entry))}</pre></details>`;
}

async function loadCompare(leftRunId, rightRunId) {
  if (!leftRunId || !rightRunId) throw new Error("Choose two runs to compare.");
  if (leftRunId === rightRunId) throw new Error("Choose two different runs.");
  const params = new URLSearchParams({left: leftRunId, right: rightRunId});
  compareState = await api(`/api/compare?${params.toString()}`);
  renderCompare();
}

async function loadSourceSelection(ids, message) {
  const path = `/api/draft/selection?ids=${encodeURIComponent(ids.join(","))}`;
  draft = await api(path);
  hydrateInputs();
  markClean();
  setMessage(message);
}

async function resetToDefaultSourceDraft() {
  draft = await api("/api/draft/default");
  hydrateInputs();
  markClean();
  setMessage("Default source pair restored.");
}

function renderCompare() {
  if (!compareState) return;
  setCompareMessage("");
  $("compareOutput").innerHTML = `
    <div class="compare-diffs">${renderCompareDiffs(compareState.diffs || [])}</div>
    <div class="compare-grid">
      ${renderCompareSide("Left", compareState.left)}
      ${renderCompareSide("Right", compareState.right)}
    </div>`;
}

function renderCompareDiffs(diffs) {
  if (!diffs.length) {
    return '<div class="muted">No first-turn differences detected in the compared fields.</div>';
  }
  return `<h3>Changed Fields</h3><dl class="status-grid">${diffs.map((diff) =>
    `<dt>${escapeHtml(diff.label)}</dt><dd>${escapeHtml(displayValue(diff.left))}<br><span class="muted">vs</span><br>${escapeHtml(displayValue(diff.right))}</dd>`
  ).join("")}</dl>`;
}

function renderCompareSide(label, side) {
  const turn = side?.first_turn;
  const config = side?.config || {};
  const transcript = side?.transcript || [];
  const meta = [
    ["Run", side?.run_id || ""],
    ["Candidates", (config.candidates || []).filter(Boolean).join(" vs ")],
    ["Scenes", config.scene_count ?? ""],
    ["Max Steps", config.max_steps ?? ""],
    ["Model", config.disable_language_model ? "disabled" : config.model],
    ["First Actor", turn?.entity_name || ""],
    ["First Step", turn?.step ?? ""],
  ];
  return `<div class="compare-side">
    <h3>${escapeHtml(label)}</h3>
    <dl class="status-grid compact">${meta.map(([key, value]) =>
      `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd>`
    ).join("")}</dl>
    ${turn ? renderUtteranceTextSurfaces(turn) : '<div class="muted">No structured first turn.</div>'}
    ${turn ? renderListBlock("Observations", turn.observations) : ""}
    ${turn ? renderComponentRows(turn.components) : ""}
    ${transcript.length ? renderTextBlock("Transcript", transcript.map((item) =>
      `Step ${item.step}: ${item.acting_entity || ""} ${item.action || ""}`
    ).join("\n")) : ""}
  </div>`;
}

async function init() {
  source = await api("/api/source");
  populateChrome();
  draft = await api("/api/draft/default");
  hydrateInputs();
  markClean();
  await refreshDrafts();
  await refreshStatus();
  setInterval(refreshStatus, 2000);
}

if (typeof document !== "undefined") {
  const isDraftChangeTarget = (target) => {
    if (target.id === "draftName") return true;
    const panel = target.closest("[data-tab-panel]");
    return Boolean(panel && panel.dataset.tabPanel !== "logs");
  };

  document.addEventListener("input", (event) => {
    if (event.target.id === "logFilter") {
      renderLogBrowser();
      return;
    }
    if (isDraftChangeTarget(event.target)) {
      markDirty();
    }
  });
  document.addEventListener("change", (event) => {
    if (isDraftChangeTarget(event.target)) {
      markDirty();
    }
  });
  window.addEventListener("beforeunload", (event) => {
    if (!isDirty) return;
    event.preventDefault();
    event.returnValue = "";
  });

  document.querySelectorAll(".tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      try {
        collectDraft();
        refreshDirtyState();
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
      if (!confirmDiscardChanges("apply the selected pair from source")) return;
      const currentDraft = collectDraft();
      const ids = [$("maleCandidate").value, $("femaleCandidate").value].join(",");
      const selectionDraft = await api(`/api/draft/selection?ids=${encodeURIComponent(ids)}`);
      draft = mergeSelectionDraft(currentDraft, selectionDraft);
      hydrateInputs();
      markDirty();
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
      markClean();
      setMessage(`Saved ${payload.path}`);
    } catch (error) {
      setMessage(error.message, true);
    }
  });

  $("loadDraftBtn").addEventListener("click", async () => {
    try {
      if (!confirmDiscardChanges("load another saved draft")) return;
      draft = await api(`/api/draft?name=${encodeURIComponent($("loadDraft").value)}`);
      hydrateInputs();
      markClean();
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
      const launchMode = record.start_paused ? "paused" : "playing";
      setMessage(`Started ${record.run_id} ${launchMode}.`);
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
      markDirty();
      setMessage("Config JSON applied.");
    } catch (error) {
      setMessage(error.message, true);
    }
  });

  $("applyContestantsJson").addEventListener("click", () => {
    try {
      draft.contestants = JSON.parse($("contestantsJson").value);
      hydrateInputs();
      markDirty();
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
      markDirty();
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
      markDirty();
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
      markDirty();
    } catch (error) {
      setMessage(error.message, true);
    }
  });

  document.addEventListener("click", (event) => {
    const inspectRun = event.target.closest("[data-inspect-run]");
    if (inspectRun) {
      loadInspector(inspectRun.dataset.inspectRun)
        .catch((error) => setInspectorMessage(error.message, true));
      return;
    }
    const logRun = event.target.closest("[data-log-run]");
    if (logRun) {
      const tab = document.querySelector('[data-tab="logs"]');
      if (tab) tab.click();
      $("logRunSelect").value = logRun.dataset.logRun;
      loadLog(logRun.dataset.logRun)
        .catch((error) => setLogMessage(error.message, true));
      return;
    }
    const logEntry = event.target.closest("[data-log-entry]");
    if (logEntry && logsState) {
      logsState.selected_index = Number(logEntry.dataset.logEntry);
      renderLogBrowser();
      return;
    }
    const compareLeft = event.target.closest("[data-compare-left]");
    if (compareLeft) {
      $("compareLeft").value = compareLeft.dataset.compareLeft;
      return;
    }
    const compareRight = event.target.closest("[data-compare-right]");
    if (compareRight) {
      $("compareRight").value = compareRight.dataset.compareRight;
      return;
    }
    const removeType = event.target.closest("[data-remove-type]");
    const removeScene = event.target.closest("[data-remove-scene]");
    if (!removeType && !removeScene) return;
    try {
      const label = removeType ? "scene type" : "scene";
      if (!window.confirm(`Remove this ${label} from the browser draft?`)) return;
      collectDraft();
      if (removeType) delete draft.scene_types[removeType.dataset.removeType];
      if (removeScene) draft.scenes.splice(Number(removeScene.dataset.removeScene), 1);
      hydrateInputs();
      markDirty();
    } catch (error) {
      setMessage(error.message, true);
    }
  });

  $("restoreSelection").addEventListener("click", async () => {
    try {
      if (!confirmDiscardChanges("restore this pair from source")) return;
      collectDraft();
      await loadSourceSelection(
        draft.selected_candidate_ids || [],
        "Current pair restored from source."
      );
    } catch (error) {
      setMessage(error.message, true);
    }
  });

  $("resetDefault").addEventListener("click", async () => {
    try {
      if (!confirmDiscardChanges("reset to the default source pair")) return;
      await resetToDefaultSourceDraft();
    } catch (error) {
      setMessage(error.message, true);
    }
  });

  document.querySelectorAll("[data-command]").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await api(`/api/control/${button.dataset.command}`, {method: "POST", body: "{}"});
        setMessage(`${button.textContent} sent.`);
        await refreshStatus();
      } catch (error) {
        setMessage(error.message, true);
      }
    });
  });

  $("loadInspector").addEventListener("click", async () => {
    try {
      const runId = $("inspectorRunInput").value.trim();
      if (!runId) throw new Error("Enter a run id.");
      await loadInspector(runId);
    } catch (error) {
      setInspectorMessage(error.message, true);
    }
  });

  $("turnSelect").addEventListener("change", async () => {
    try {
      if (!inspectorState) return;
      const index = Number($("turnSelect").value);
      const entry = (inspectorState.entries || []).find((item) => item.index === index);
      if (!entry) return;
      await loadInspector(inspectorState.run_id, entry);
    } catch (error) {
      setInspectorMessage(error.message, true);
    }
  });

  $("loadCompare").addEventListener("click", async () => {
    try {
      await loadCompare($("compareLeft").value, $("compareRight").value);
    } catch (error) {
      setCompareMessage(error.message, true);
    }
  });

  $("loadLog").addEventListener("click", async () => {
    try {
      await loadLog($("logRunSelect").value);
    } catch (error) {
      setLogMessage(error.message, true);
    }
  });

  init().catch((error) => setMessage(error.message, true));
}

if (typeof module !== "undefined") {
  module.exports = {
    displayValue,
    mergeSelectionDraft,
    remapSceneForSelection,
    renderCompareSide,
    renderLogBrowser,
    renderTurnDetail,
    formatLogDetails,
    filteredLogEntries,
    draftFingerprint,
    logSearchText,
    runContextLabel,
    summarizeDraftContext,
  };
}
