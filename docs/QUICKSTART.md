# End-to-end example

Requires Python 3.10+.

```bash
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -v
python3 scripts/workflow.py init --task "Fix a deterministic sorting bug" --output workflow.json
python3 scripts/workflow.py record --file workflow.json --stage scope --status complete --evidence "Acceptance criteria reviewed"
python3 scripts/workflow.py record --file workflow.json --stage investigate --status complete --evidence "Synthetic equal-timestamp reproduction"
python3 scripts/workflow.py report --file workflow.json
```

The output file is a local workflow record. Stage evidence is manually supplied; it is not independently validated.

To use the guidance with Claude Code, copy the skill folders to `~/.claude/skills/` and request the `workflow-orchestrator` skill for a multi-stage coding task.
