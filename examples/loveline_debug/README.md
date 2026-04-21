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
- Browser editing for candidate payload, scene payload, and run settings.
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
tests but produces empty free-text actions. Uncheck it and set `API Type`,
`Model`, and provider credentials when you want a full model-backed run.

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
- Logs: embed `concordia/utils/log_viewer.html` and load `structured_log.json`
  directly from recent runs.
- Compare: diff two `config_snapshot.json` files and two structured logs by
  entity action timeline using `concordia_log.py`/`structured_logging`.

