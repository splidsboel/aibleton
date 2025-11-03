# Post-MVP Roadmap

This plan summarizes the next major milestones after the MVP (see `MANIFEST.md`) so each agent can align on priorities and handoffs.

## 1. Ableton Bridge Integration
- ✅ Configurable AbletonOSC bridge with dry-run and UDP transport support (see `src/aibleton/bridge`).
- ✅ Smoke tooling (`scripts/bridge_smoke.py`) and setup docs (`docs/ableton_bridge_setup.md`).
- ✅ Regression coverage via `tests/test_bridge.py` and CLI integration dry-runs.
- ✅ Device parameter control and live Ableton state discovery (`AbletonOSCContextProvider`).
- ⏭ Extend parity toward note creation (`clip_slot/set_notes`) so generated patterns populate clips.

## 2. Structured Command Loop with LLM
- Define the JSON schema (function signatures, error payloads) for LLM output.
- Wire the hybrid orchestrator to a real LLM/fn-calling endpoint with retry logic.
- Create prompt/response fixtures and golden transcripts for common tasks.
- Introduce telemetry for parsing failures to guide prompt tuning.

## 3. Live State & Safety Hardening
- Replace fixture snapshots with live-state polling (tracks, clips, devices).
- Track diffs and expose context summaries back to the LLM and UX layer.
- Expand confirmation policies for destructive or bulk operations.
- Document rollback/recovery procedures when actions fail mid-flight.

## 4. QA Automation & CI
- Add CLI-based integration tests that run scripted conversations.
- Configure CI to run rule-based, structured, and bridge dry-run test suites.
- Publish manual test matrices for Live-in-the-loop scenarios (clip edits, device loading).
- Capture log artifacts for debugging failing runs.

## 5. UX & Interaction Surface
- Prototype the preferred front-end (CLI polish, desktop companion, or Max for Live device).
- Ensure latency feedback, success/error messaging, and conversation history meet UX guidelines.
- Conduct user testing sessions and feed insights to the Product Navigator and QA Agent.

## 6. Telemetry, Research, and Upgrades
- Add optional telemetry hooks (opt-in) for action metrics and error trends.
- Track Ableton API changes, Python version updates, and third-party tool releases.
- Publish upgrade advisories and dependency pinning strategies.
- Maintain a reference catalog of community recipes for device/browser automation.

Each epic should have an owning agent (per `agents.md`) who drives task breakdown and coordinates cross-team dependencies during weekly triage.
