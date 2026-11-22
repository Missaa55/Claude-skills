#!/usr/bin/env python3
"""Deterministic skill routing and validated, evidence-ready task planning.

This module never executes AI agents, builds, or arbitrary user commands.
"""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "framework" / "registry.json"
GENERIC = {"app", "application", "review", "test", "audit", "performance", "security",
           "plan", "docs", "documentation", "deploy", "deployment"}

def words(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.casefold())

def matches(text: str, phrase: str) -> bool:
    needle, haystack = words(phrase), words(text)
    return bool(needle) and any(haystack[i:i + len(needle)] == needle
                                for i in range(len(haystack) - len(needle) + 1))

def _aliases(data: dict, domain: str, skill: str) -> list[str]:
    explicit = data.get("skill_keywords", {})
    aliases = [skill, skill.replace("-", " ")]
    aliases += explicit.get(skill, []) + explicit.get(f"{domain}/{skill}", [])
    # Explicit aliases only for ambiguous compound skills: never use a suffix
    # such as "system", "quality", or "engineer" as an accidental trigger.
    return aliases

def route(task: str, registry: dict | None = None) -> dict:
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task cannot be empty")
    data = registry if registry is not None else json.loads(REGISTRY.read_text(encoding="utf-8"))
    scores = {}
    hits_by_domain = {}
    for domain, config in data["domains"].items():
        hits = [phrase for phrase in config["keywords"] if matches(task, phrase)]
        if hits:
            scores[domain] = sum(4 if len(words(p)) > 1 else 1 for p in hits)
            hits_by_domain[domain] = hits

    # Minecraft requires game-specific vocabulary; "server" and "plugin"
    # alone are infrastructure words, not proof of Minecraft intent.
    game_terms = ("minecraft", "fabric", "neoforge", "datapack", "modpack",
                  "worldgen", "paper plugin", "minecraft server")
    if not any(matches(task, p) for p in game_terms):
        scores.pop("minecraft", None)

    # A builder owns the workflow. General app/web words should not
    # accidentally create parallel, competing orchestrators.
    if "appbuilder" in scores:
        scores.pop("applications", None)
    if "webbuilder" in scores and not any(matches(task, p) for p in
        ("backend", "api", "database", "supabase", "mobile", "desktop")):
        scores.pop("applications", None)

    # Universal skills are cross-cutting and selected individually; they do
    # not need an extra task-planner unless universal is the only domain.
    if len(scores) > 1:
        scores.pop("universal", None)

    domains = sorted(scores, key=lambda d: (-scores[d], d)) or ["universal"]
    paths = []
    for domain in domains:
        config = data["domains"][domain]
        selected = list(config["default"])
        for skill in config["skills"]:
            if any(matches(task, p) for p in _aliases(data, domain, skill)):
                if skill not in selected:
                    selected.append(skill)
        paths.extend(f"{config['root']}/{skill}/SKILL.md" for skill in selected)

    for skill, aliases in data.get("shared_skill_keywords", {}).items():
        if skill not in data.get("shared_skills", []):
            continue
        if any(matches(task, alias) for alias in aliases):
            paths.append(f"skills/{skill}/SKILL.md")

    if len(domains) > 1:
        paths.insert(0, "skills/workflow-orchestrator/SKILL.md")
    paths = list(dict.fromkeys(paths))
    return {"task": task, "domains": domains, "skill_paths": paths,
            "matched_keywords": {d: hits_by_domain.get(d, []) for d in domains},
            "note": "Advisory routing only; no agents, builds, or tests executed."}

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task")
    args = parser.parse_args()
    print(json.dumps(route(args.task), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
