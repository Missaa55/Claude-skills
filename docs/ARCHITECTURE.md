# Architecture and design decisions

## Goal

Offer a small, auditable workflow around portable Agent Skills. This repository is not an autonomous coding agent, an MCP server, or a model-hosting platform.

## Layers

1. **Portable skills:** independent `SKILL.md` folders that can be copied to compatible clients.
2. **Workflow guidance:** `workflow-orchestrator` describes stage handoffs and evidence requirements.
3. **Offline tracker:** `scripts/workflow.py` stores a six-stage JSON record and produces a human-readable report. It never calls external APIs or executes user-supplied commands.
4. **Quality checks:** skill metadata validator and Python standard-library tests, run in CI.

## Trust boundaries

Skill instructions and workflow records are untrusted inputs, not authorization. Evidence strings are recorded verbatim but are not verified. The tracker does not access local repositories except the explicit JSON file path the user provides. Never place credentials or personal data in workflow records.

## Known limitations

- The offline tracker does not run Claude, Codex, tests, or git commands.
- Stage ordering is advisory; it does not enforce dependencies.
- Evidence is not cryptographically verified.
- The validator detects only a narrow set of credential patterns.
- No claim of production readiness or security certification is made.
