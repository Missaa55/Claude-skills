---
name: appbuilder-orchestrator
description: Coordinate application discovery, architecture, design, implementation, verification and delivery with explicit quality gates.
---

# AppBuilder Orchestrator

## When to use

Use for multi-stage application creation or substantial feature work.

## Procedure

1. Read AppBuilder/README.md and gather scope, user journeys and acceptance criteria.
2. Use the self-contained installed `runtime/builder.py` and its `examples/briefs/app.json` for the executable reference. Shared Applications/Universal guidance is optional when available; another builder is not required. Distinguish deterministic scaffolding from a real authenticated agent run.
3. Establish dependencies: architecture precedes implementation; implementation precedes verification.
4. Request evidence for each quality gate. Return failing stages for correction.
5. Never run untrusted code or deploy without approval; separate proposed from executed actions.

## Output

Provide stage status, artifacts, tests actually run, unresolved risks and next approval point.
