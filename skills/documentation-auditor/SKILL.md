---
name: documentation-auditor
description: Compare project documentation against actual code, configuration, and tests to find stale or misleading instructions.
---

# Documentation Auditor

## When to use

Use before releases, onboarding, or after changing CLI commands, APIs, or deployment configuration.

## Procedure

1. Read README, contribution instructions, package metadata, and actual scripts/configuration.
2. Compare documented commands and flags to their definitions; check paths and required versions.
3. Identify missing setup steps, unsupported promises, dead internal links, and ambiguous examples.
4. Validate commands in a safe local environment when available; never run destructive deployment steps.
5. Use only synthetic examples and placeholder credentials.
6. Recommend precise edits with file paths. Mark unverified claims as unverified.

## Output

Provide a table of mismatches with location, evidence, severity, and proposed correction. End with a concise updated quick-start if needed.

## Example

README says `npm run lint` but package.json defines only `check`.
Finding: documented command fails; update the README or add the missing script.
