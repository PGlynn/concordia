# Loveline Stock-Concordia Debug UI

This is a narrow first usable slice for running the Loveline dating-show data
through stock Concordia.

The code lives in `examples/loveline_debug/`. It reads editable starter data
from:

```text
/Users/claw/.openclaw/games/loveline/concordia_dating_show_starter
```

Drafts and run artifacts are written back under:

```text
/Users/claw/.openclaw/games/loveline/concordia_dating_show_starter/generated/loveline_debug/
```

## What It Supports

- Exactly 2 candidates per draft: 1 man and 1 woman.
- Candidate selection from the existing `personas/personas.yaml` and generated
  `generated/persona_bundle.json` source.
- Browser form editing for draft metadata, pair selection, run settings,
  candidates, scene defaults, scene types, and scene list entries. Raw JSON
  views remain available for exact draft inspection and targeted payload edits.
- Save/load of draft JSON snapshots.
- Baseline runs through stock Concordia:
  - `concordia.prefabs.entity.basic.Entity`
  - `concordia.prefabs.game_master.formative_memories_initializer.GameMaster`
  - `concordia.prefabs.game_master.dialogic_and_dramaturgic.GameMaster`
  - `concordia.prefabs.simulation.generic.Simulation`
- Structured JSON log, HTML log, config snapshot, config visualization, and
  generic checkpoints.
- A live status/transcript shell with play, pause, step, and stop controls using
  `simulation_server.SimulationServer` and its stock `StepController`.
- Recent run history with direct artifact links, plus a first-turn side-by-side
  compare over each run's `config_snapshot.json`, `structured_log.json`, and
  `status.json` transcript.
- Logs tab for choosing recent runs, filtering `structured_log.json` entries,
  inspecting selected raw JSON, and opening the saved `log.html` viewer.

No Loveline-specific Concordia cognition modules are added here.

## Run

From the Concordia repo:

```bash
python -m examples.loveline_debug.server --port 8765
```

Open:

```text
http://localhost:8765
```

Runs start paused. Click `Step` for deterministic inspection, or `Play` to let
the run proceed.

By default, `Disable language model` is unchecked so fresh drafts use
Loveline's local starter stack: preset `Local Ollama`, `API Type` `ollama`, and
`Model` `qwen3.5:35b-a3b`. The Run Settings form now also exposes a `Codex
OAuth` preset that maps to `api_type` `codex_oauth` and recommended model
`gpt-5.4`. Loveline explicitly does not default that preset to `gpt-5.5`.
Check `Disable language model` when you want Concordia's `NoLanguageModel` path
for quick config, checkpoint, and logging smoke tests without any model
dependency.

For `API Type` `ollama`, this debug UI uses a Loveline-local Ollama shim under
`examples/loveline_debug` instead of changing Concordia's shared Ollama model.
For `API Type` `codex_oauth`, it uses a Loveline-local adapter that shells out
to `codex exec` with the already logged-in server-side Codex CLI OAuth session,
using ephemeral execution, `--skip-git-repo-check`, read-only sandboxing, no
color, and `--output-last-message` capture. Neither Loveline path requires a
user-entered API key. The local adapters both support `sample_text` and
`sample_choice`. Other providers continue to use Concordia's stock
`language_model_setup`.

## Artifact Layout

Each run creates:

```text
generated/loveline_debug/runs/<run_id>/
  config_snapshot.json
  config_visualization.html
  structured_log.json
  log.html
  manifest.json
  status.json
  checkpoints/
```

Saved drafts are:

```text
generated/loveline_debug/drafts/<draft_name>.json
```

Shared contestant edits are stored once and hydrated into any draft that selects
the contestant id:

```text
generated/loveline_debug/contestants.json
```

## Next Extension Points

- Inspect: embed `visual_interface` output and checkpoint component state in the
  right panel instead of only linking the generated config visualization.
- Compare: extend the first-turn view into a broader entity action timeline diff
  using `concordia_log.py`/`structured_logging`.
