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

By default, `Disable language model` is checked. This uses Concordia's
`NoLanguageModel`, which is useful for config, checkpoint, and logging smoke
tests but produces empty free-text actions. The draft still defaults the
model-backed fields to Loveline's local starter stack: `API Type` is `ollama`
and `Model` is `qwen3.5:35b-a3b`. Uncheck `Disable language model` when you
want a full local model-backed run.

For `API Type` `ollama`, this debug UI uses a Loveline-local Ollama shim under
`examples/loveline_debug` instead of changing Concordia's shared Ollama model.
The shim keeps the same provider/model selection, passes `think=False` for text
and choice generation, forwards stop tokens, and maps practical request controls
such as `max_tokens` and `seed` into Ollama request options. It also keeps the
local Loveline adapter's in-world prompting, response cleanup, and numbered JSON
choice parsing. Non-Ollama providers continue to use Concordia's stock
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

## Next Extension Points

- Inspect: embed `visual_interface` output and checkpoint component state in the
  right panel instead of only linking the generated config visualization.
- Compare: extend the first-turn view into a broader entity action timeline diff
  using `concordia_log.py`/`structured_logging`.
