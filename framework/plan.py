#!/usr/bin/env python3
"""Generate an offline cross-domain execution handoff manifest.

A manifest is a plan, not proof that an AI agent or build ran.
"""
import argparse
import json
from pathlib import Path
from route import route

PHASES = (
    ("discovery", (), "Requirements, acceptance criteria and constraints"),
    ("architecture", ("discovery",), "Technical decisions and interface contracts"),
    ("implementation", ("architecture",), "Changed files and reproducible build commands"),
    ("verification", ("implementation",), "Actual test results, accessibility and security findings"),
    ("review", ("verification",), "Evidence-backed review with blocking defects"),
    ("delivery", ("review",), "Release checklist, rollback plan and approval"),
)

def build_manifest(task: str, registry: dict | None = None) -> dict:
    selection = route(task, registry)
    stages = []
    for name, dependencies, expected in PHASES:
        stages.append({
            "id": name, "depends_on": list(dependencies),
            "status": "pending", "owner": selection["domains"][0],
            "expected_output": expected, "evidence": [], "blockers": [],
        })
    return {
        "schema_version": 1, "task": selection["task"],
        "domains": selection["domains"], "skill_paths": selection["skill_paths"],
        "stages": stages, "approved_for_release": False,
        "execution": "not_started",
        "notice": "No agent execution, test or build has occurred.",
    }

def validate_manifest(data: dict) -> list[str]:
    errors = []
    if data.get("schema_version") != 1:
        errors.append("Unsupported manifest version")
    stages = data.get("stages", [])
    names = [s.get("id") for s in stages]
    if names != [s[0] for s in PHASES]:
        errors.append("Invalid stage sequence")
    for stage in stages:
        if any(dep not in names for dep in stage.get("depends_on", [])):
            errors.append(f"Missing dependency in {stage.get('id')}")
        if stage.get("status") not in ("pending", "blocked", "complete"):
            errors.append(f"Invalid status in {stage.get('id')}")
        if stage.get("status") == "complete" and not stage.get("evidence"):
            errors.append(f"Completed stage has no evidence: {stage.get('id')}")
    if data.get("approved_for_release") and any(
        s.get("status") != "complete" for s in stages):
        errors.append("Release approval requires all stages complete")
    return errors

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task")
    parser.add_argument("--output", help="Write JSON manifest; refuses overwrite")
    args = parser.parse_args()
    manifest = build_manifest(args.task)
    if args.output:
        output = Path(args.output)
        if output.exists():
            parser.error("Output exists; refusing to overwrite")
        output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {output}")
    else:
        print(json.dumps(manifest, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
