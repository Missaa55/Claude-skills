---
name: bug-investigator
description: Investigate a reproducible software defect using evidence, focused experiments, and minimal changes.
---

# Bug Investigator

## When to use

Use for failing tests, unexpected output, intermittent errors, or regressions.

## Procedure

1. Capture expected behavior, actual behavior, environment, and the smallest reproducible input.
2. Form multiple plausible hypotheses; rank them by available evidence.
3. Inspect relevant code and logs, redacting secrets and user information.
4. Run the cheapest discriminating test first. Do not alter production systems or delete data without approval.
5. Identify the root cause only when the evidence supports it; otherwise report uncertainty.
6. Propose the smallest fix and a regression test that fails before the fix and passes afterward.
7. Separate observed results from assumptions. Do not claim tests passed unless they were run.

## Output

Provide reproduction steps, evidence, likely root cause with confidence, proposed patch, regression test, and unresolved risks.

## Example

Input: sorting orders produces the wrong result for identical timestamps.
Experiment: create two synthetic orders with equal timestamps and different IDs.
Expected: deterministic secondary sort by ID.
