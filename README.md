# Ableton Live NL Assistant (MVP)

This repository contains an experimental natural-language assistant that bridges large language model intents to Ableton Live 11/12 on macOS. The current implementation focuses on a rule/JSON hybrid orchestrator and an OSC bridge that can talk to [AbletonOSC](https://github.com/ideoforms/AbletonOSC) or compatible Remote Scripts.

## Features
- CLI REPL that interprets natural-language commands or structured JSON action plans.
- Hybrid planner (rule-based + structured parsing) that produces tempo/volume/clip actions.
- Configurable Ableton bridge with dry-run logging, UDP transport, and scene-aware clip creation.
- Smoke-testing script and unit tests to exercise bridge behaviour without launching Ableton.
- Post-MVP roadmap tracked in `docs/post_mvp_plan.md`.

## Getting Started
```bash
git clone https://github.com/<your-org>/aibleton.git
cd aibleton
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Run the test suite:
```bash
PYTHONPATH=src python -m unittest discover -s tests
```

## CLI Usage
```bash
PYTHONPATH=src python -m aibleton.cli.main
```

Key commands:
- `set tempo to 128`
- `set drums volume to -4`
- `launch intro beat clip on drums`
- `create 4 bar clip named bridge on drums`
- `set drums saturator drive to 18`

Pass `--bridge osc --config aibleton.toml` to enable the OSC bridge (see below).

## Ableton Bridge Setup
1. Install AbletonOSC into `~/Music/Ableton/User Library/Remote Scripts/`.
2. Copy `config/aibleton.example.toml` to `aibleton.toml` and set `send = true` when ready.
3. Optionally run the smoke script:
   ```bash
   PYTHONPATH=src python scripts/bridge_smoke.py --tempo 126 --volume "Drums:-4"
   ```
4. Start the CLI with:
   ```bash
   PYTHONPATH=src python -m aibleton.cli.main --bridge osc --config aibleton.toml
   ```

For more detail see `docs/ableton_bridge_setup.md`.

## Roadmap
Post-MVP tasks (live state syncing, device control, note generation, UI improvements) are tracked in `docs/post_mvp_plan.md`. Each epic ties back to the agent roles defined in `agents.md`.

## Contributing
- Create feature branches and open PRs against `master`.
- Ensure `python -m unittest discover -s tests` passes locally.
- Follow the existing commit style (`<verb phrase>`).
