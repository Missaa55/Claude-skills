#!/usr/bin/env python3
"""Offline skill router. Prints suggested skills; never invokes an AI agent."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "framework" / "registry.json"

def route(task: str, registry: dict | None = None) -> dict:
    if not task.strip():
        raise ValueError("task cannot be empty")
    data = registry if registry is not None else json.loads(REGISTRY.read_text(encoding="utf-8"))
    tokens = set(re.findall(r"[a-z0-9-]+", task.casefold()))
    scored = []
    for domain, config in data["domains"].items():
        score = sum(1 for word in config["keywords"] if word in tokens)
        if score:
            scored.append((domain, score))
    scored.sort(key=lambda item: (-item[1], item[0]))
    domains = [domain for domain, _ in scored] or ["universal"]
    paths = []
    for domain in domains:
        config = data["domains"][domain]
        selected = list(config["default"])
        for skill in config["skills"]:
            suffix = skill.split("-", 1)[-1]
            if skill in tokens or suffix in tokens:
                if skill not in selected:
                    selected.append(skill)
        for skill in selected:
            paths.append(f"{config['root']}/{skill}/SKILL.md")
    if len(domains) > 1:
        paths.insert(0, "skills/workflow-orchestrator/SKILL.md")
    return {"task": task, "domains": domains, "skill_paths": paths,
            "note": "Suggestions only. Confirm compatibility and approvals before execution."}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task")
    args = parser.parse_args()
    print(json.dumps(route(args.task), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
