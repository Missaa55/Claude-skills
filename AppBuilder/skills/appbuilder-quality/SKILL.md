---
name: appbuilder-quality
description: Gate application delivery using reproducible build, functional, accessibility, security and visual evidence.
---

# AppBuilder Quality

## When to use

Use before merging or releasing an application feature.

## Procedure

1. Read acceptance criteria and identify critical user journeys.
2. Run only authorized build, type, lint and test commands in a safe environment.
3. Check E2E journeys, automated accessibility findings, secret exposure and dependency risks.
4. Review desktop/mobile states and document any manual checks.
5. Classify failures as blocking or advisory and return blocking defects to implementation.
6. Never mark unexecuted tests as passed or conceal findings.

## Output

Provide a gate-by-gate report with command, result, evidence, severity and remaining limitations.
