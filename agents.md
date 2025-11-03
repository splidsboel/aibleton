# Agent Roster for the Ableton Live Assistant Project

## Product Navigator
- **Scope**: Maintain the high-level roadmap, translate the `MANIFEST.md` milestones into sprint-ready goals, and arbitrate trade-offs between features, latency, and reliability.
- **Key Outputs**: Prioritized backlog, release criteria, stakeholder updates, product requirement briefs for new commands or UX flows.
- **Handoffs**: Sends approved backlog items to the Ableton Bridge Agent and LLM Orchestrator; receives QA status reports.

## Ableton Bridge Agent
- **Scope**: Own the control-surface integration with Ableton Live via Python Remote Scripts, AbletonOSC, or Ableton.js. Prototype and harden device loading, clip management, and transport control APIs.
- **Key Outputs**: Remote Script implementation, connectivity harnesses, regression-safe wrappers for Live Object Model actions, integration tests run inside Live. Reference `docs/ableton_bridge_setup.md` for environment setup and `docs/abletonosc_docs.md` for the consolidated AbletonOSC command list.
- **Handoffs**: Supplies execution adapters to the LLM Orchestrator; collaborates with the QA Agent for in-Live test scenarios.

## LLM Orchestrator
- **Scope**: Design the command schema, prompting strategy, and JSON/DSL parsing pipeline that maps natural-language requests to the execution layer.
- **Key Outputs**: Prompt templates, function/JSON schemas, conversation memory strategy, fallback and retry policies for ambiguous commands.
- **Handoffs**: Consumes state snapshots from the Context Collector; delivers structured action plans to the Ableton Bridge Agent.

## Context Collector
- **Scope**: Observe Live set state (tracks, clips, devices, tempo) and expose a query API so the assistant can ground its responses in real data.
- **Key Outputs**: Lightweight state cache, diffing utilities for recent changes, telemetry hooks for metrics and debugging.
- **Handoffs**: Feeds context to the LLM Orchestrator and informs the Product Navigator about frequently requested features or pain points.

## QA & Safety Agent
- **Scope**: Validate new capabilities against regression scenarios, enforce guardrails on destructive operations, and design user-confirmation flows.
- **Key Outputs**: Automated test scripts (unit + Live-in-the-loop), manual test matrices, rollback and recovery checklists.
- **Handoffs**: Blocks releases until test suites pass; reports gaps back to the Product Navigator and Ableton Bridge Agent.

## UX & Interaction Agent
- **Scope**: Prototype user-facing interfaces (CLI, desktop companion, Max for Live device), define messaging tone, and ensure response latency feels interactive.
- **Key Outputs**: UI mockups, conversation flows, logging/notification layout, accessibility guidelines.
- **Handoffs**: Works with the LLM Orchestrator on prompt feedback, coordinates with Product Navigator for roadmap alignment, and gathers user testing insights for QA.

## Research & Ecosystem Agent
- **Scope**: Monitor third-party projects (Producer Pal, Ableton Copilot MCP, community tools) and Ableton API changes to keep the stack current.
- **Key Outputs**: Competitive analyses, upgrade advisories (e.g., Live 12 Python 3.11 changes), curated reference library for device loading and browser automation.
- **Handoffs**: Shares findings with all agents; flags deprecations or new opportunities to the Product Navigator and Ableton Bridge Agent.

## DevOps & Tooling Agent
- **Scope**: Manage local development environments, CI pipelines, dependency pinning, and packaging for distribution to internal testers.
- **Key Outputs**: Reproducible environment scripts, CI configuration, deployment automation for remote scripts and companion services.
- **Handoffs**: Keeps QA tooling stable, supplies build artifacts to UX for demos, and informs Product Navigator about infrastructure constraints.

## Collaboration Cadence
- Weekly triage led by Product Navigator with all agents for backlog grooming and dependency calls.
- Daily async updates in project channel: blockers, newly discovered API behaviors, telemetry anomalies.
- Integration reviews whenever the LLM Orchestrator introduces new command families or the Ableton Bridge Agent modifies low-level controllers to ensure schema/execution alignment.
