# MVP Architecture Blueprint

This document translates `MANIFEST.md` and `agents.md` into a concrete Minimum Viable Product scope.

## Goals for MVP
- Accept natural-language commands via a CLI and emit structured actions.
- Produce deterministic JSON plans using a constrained rule-based parser (LLM integration can be swapped in later).
- Execute a subset of actions through an Ableton bridge abstraction; the MVP implementation logs intents instead of invoking Live so we can test without Ableton open.
- Capture lightweight set state snapshots to ground responses.
- Provide a safety layer that requires confirmation before destructive actions.

## High-Level Components
- **CLI Frontend (`aibleton.cli`)**: Blocking REPL that reads user commands, routes them to the orchestrator, and prints responses.
- **Orchestrator (`aibleton.orchestrator`)**: Converts NL prompts to structured plans, validates with schema, and hands over to the bridge. Starts with pattern-based parsing plus TODO hooks for LLM calls.
- **Ableton Bridge (`aibleton.bridge`)**: Interface for Live control. MVP implements `LoggingBridge` that records actions; later replace with OSC / Remote Script clients.
- **Context Collector (`aibleton.context`)**: Supplies mocked project state (tracks, clips, devices). MVP loads JSON fixtures; can be swapped for real Live queries.
- **Safety & QA Hooks (`aibleton.safety`)**: Confirmation prompts for destructive actions and audit logging stubs.

## MVP Command Surface
- `set_tempo`: change global tempo.
- `set_track_volume`: adjust a track’s volume.
- `create_midi_clip`: create a MIDI clip with note pattern templates (kick/snare baseline).
- `launch_clip`: trigger a clip by scene slot.

## Data Flow
1. CLI receives a user string.
2. Orchestrator normalizes the text, matches against supported intents, and emits an `ActionPlan`.
3. Plan is validated; the Safety layer may request confirmation.
4. Bridge executes each action (MVP prints/logs).
5. CLI reflects status and updated context summary.

## Milestones
1. Scaffolding: package layout, CLI entry point, dataclasses for actions.
2. Orchestrator v0: regex parser for four intents, error handling.
3. Bridge v0: logging executor plus integration harness.
4. Context fixtures + safety confirmation prompts.
5. Smoke tests: scripted commands executed via CLI to ensure end-to-end flow.

## Non-Goals for MVP
- Full Ableton integration (remote script, OSC).
- Advanced LLM parsing or conversational memory.
- Device loading or browser automation.

## Open Questions / TODOs
- Define JSON schema for actions (pydantic?). For MVP we can store as dataclasses with `.model_dump()` shim.
- Decide on persistence for context snapshots.
- Integrate telemetry hooks once real bridge is wired.
