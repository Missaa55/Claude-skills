---
name: webbuilder-quality-cleaner
description: Review AI slop and unnecessary data in websites, responsive components, SEO content and generated frontend assets without destructive automation.
---

# webbuilder-quality-cleaner

## When to use

Use for pre-release quality review, placeholder detection and cleanup planning for websites, responsive components, SEO content and generated frontend assets.

## Procedure

1. When installed as a standalone Claude skill, run `python3 scripts/cleaner.py web <project-directory>` from this skill's directory. When using the repository checkout, `python3 -m quality.cleaner web <project-directory>` also works. Both commands only inspect files.
2. Inspect every finding in context. Heuristics are not proof of AI origin or safe deletion; verify references, dependencies, user content and runtime behavior.
3. Prepare a human-readable proposed diff and list of candidate files with justifications. Do not remove, rewrite or move files without explicit approval. Preserve backups and provide a rollback plan.
4. Re-run builder-specific tests after any separately approved cleanup and report exact results.

## Output

Provide evidence-backed findings, severity, affected paths, proposed fixes, protected files, and actual verification results. Distinguish confirmed issues from stylistic opinions.
