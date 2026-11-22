#!/usr/bin/env python3
"""Deterministic, offline workflow tracker. Does not invoke an AI model."""
import argparse
import json
from pathlib import Path
import sys

STAGES = ("scope", "investigate", "review", "test", "document", "verify")
STATUSES = ("pending", "complete", "blocked")


def new_plan(task: str) -> dict:
    if not task.strip():
        raise ValueError("task must not be empty")
    return {"schema_version": 1, "task": task.strip(), "stages": [
        {"name": name, "status": "pending", "evidence": []} for name in STAGES
    ]}


def validate_plan(data: dict) -> None:
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("unsupported schema")
    if not isinstance(data.get("task"), str) or not data["task"].strip():
        raise ValueError("invalid task")
    stages = data.get("stages")
    if not isinstance(stages, list) or [s.get("name") for s in stages if isinstance(s, dict)] != list(STAGES):
        raise ValueError("invalid stages")
    for stage in stages:
        if stage.get("status") not in STATUSES or not isinstance(stage.get("evidence"), list):
            raise ValueError("invalid stage data")
        if any(not isinstance(x, str) or not x.strip() for x in stage["evidence"]):
            raise ValueError("invalid evidence")
        if stage["status"] == "complete" and not stage["evidence"]:
            raise ValueError("complete stage requires evidence")


def record(data: dict, stage_name: str, status: str, evidence: str | None) -> dict:
    validate_plan(data)
    if stage_name not in STAGES or status not in STATUSES:
        raise ValueError("invalid stage or status")
    if status == "complete" and not (evidence and evidence.strip()):
        raise ValueError("completion requires evidence")
    stage = data["stages"][STAGES.index(stage_name)]
    stage["status"] = status
    if evidence and evidence.strip():
        stage["evidence"].append(evidence.strip())
    validate_plan(data)
    return data


def report(data: dict) -> str:
    validate_plan(data)
    lines = [f"# Workflow: {data['task']}", ""]
    for stage in data["stages"]:
        lines.append(f"- {stage['name']}: {stage['status']}")
        for item in stage["evidence"]:
            lines.append(f"  - Evidence: {item}")
    lines.extend(["", "Note: recorded evidence is user-supplied and is not independently verified."])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--task", required=True)
    init.add_argument("--output", required=True)
    rec = commands.add_parser("record")
    rec.add_argument("--file", required=True)
    rec.add_argument("--stage", choices=STAGES, required=True)
    rec.add_argument("--status", choices=STATUSES, required=True)
    rec.add_argument("--evidence")
    rep = commands.add_parser("report")
    rep.add_argument("--file", required=True)
    args = parser.parse_args()
    try:
        if args.command == "init":
            path = Path(args.output)
            if path.exists():
                raise ValueError("output already exists; refusing to overwrite")
            path.write_text(json.dumps(new_plan(args.task), indent=2) + "\n", encoding="utf-8")
            print(f"Created {path}")
        else:
            path = Path(args.file)
            data = json.loads(path.read_text(encoding="utf-8"))
            if args.command == "record":
                record(data, args.stage, args.status, args.evidence)
                path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
                print(f"Updated {args.stage}")
            else:
                print(report(data))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
