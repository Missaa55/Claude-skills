---
name: minecraft-quality-cleaner
description: Review AI slop and unnecessary data in mods, plugins, datapacks, registries, assets and world-safe cleanup without destructive automation.
---

# minecraft-quality-cleaner

## When to use

Use for pre-release quality review, placeholder detection and cleanup planning for mods, plugins, datapacks, registries, assets and world-safe cleanup.

## Procedure

1. Run `python3 -m quality.cleaner minecraft <project-directory>` from the repository checkout, or use equivalent read-only inspection when the optional tool is unavailable.
2. Inspect every finding in context. Heuristics are not proof of AI origin or safe deletion; verify references, dependencies, user content and runtime behavior.
3. Prepare a human-readable proposed diff and list of candidate files with justifications. Do not remove, rewrite or move files without explicit approval. Preserve backups and provide a rollback plan.
4. Re-run builder-specific tests after any separately approved cleanup and report exact results.

## Output

Provide evidence-backed findings, severity, affected paths, proposed fixes, protected files, and actual verification results. Distinguish confirmed issues from stylistic opinions.
