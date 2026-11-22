#!/usr/bin/env python3
"""Offline, explainable skill router. It never executes agents or user commands."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "framework" / "registry.json"
STOPWORDS = {"a", "an", "the", "with", "for", "and", "to", "of", "in", "on"}

def words(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.casefold())

def matches(text: str, phrase: str) -> bool:
    needle = words(phrase)
    haystack = words(text)
    return bool(needle) and any(haystack[i:i+len(needle)] == needle
                                for i in range(len(haystack)-len(needle)+1))

def route(task: str, registry: dict | None = None) -> dict:
    if not task.strip():
        raise ValueError("task cannot be empty")
    data = registry if registry is not None else json.loads(REGISTRY.read_text(encoding="utf-8"))
    domain_scores = {}
    for domain, config in data["domains"].items():
        hits = [p for p in config["keywords"] if matches(task, p)]
        if hits:
            domain_scores[domain] = sum(3 if len(words(p)) > 1 else 1 for p in hits)
    # Minecraft must be explicitly identified, not inferred from generic infrastructure words.
    minecraft_context = any(matches(task, p) for p in (
        "minecraft", "fabric", "neoforge", "datapack", "modpack", "worldgen",
        "minecraft server", "paper plugin", "fabric mod", "neoforge mod", "npc"))
    if not minecraft_context:
        domain_scores.pop("minecraft", None)
    # AppBuilder is the primary owner of app-generation requests; Applications supports it.
    if "appbuilder" in domain_scores:
        domain_scores.pop("applications", None)
    domains = sorted(domain_scores, key=lambda d: (-domain_scores[d], d)) or ["universal"]
    selected_paths = []
    for domain in domains:
        config = data["domains"][domain]
        selected = list(config["default"])
        for skill in config["skills"]:
            aliases = [skill, skill.replace("-", " ")]
            aliases += data.get("skill_keywords", {}).get(skill, [])
            aliases += data.get("skill_keywords", {}).get(f"{domain}/{skill}", [])
            # Match any meaningful component for compound skill names.
            suffix = skill.split("-", 1)[-1]
            aliases += [part for part in suffix.split("-") if len(part) >= 4 and part not in STOPWORDS]
            if any(matches(task, alias) for alias in aliases) and skill not in selected:
                selected.append(skill)
        selected_paths.extend(f"{config['root']}/{skill}/SKILL.md" for skill in selected)
    for skill, aliases in data.get("shared_skill_keywords", {}).items():
        if any(matches(task, alias) for alias in aliases):
            selected_paths.append(f"skills/{skill}/SKILL.md")
    if len(domains) > 1:
        selected_paths.insert(0, "skills/workflow-orchestrator/SKILL.md")
    # Keep deterministic ordering while eliminating duplicates.
    paths = list(dict.fromkeys(selected_paths))
    return {"task": task, "domains": domains, "skill_paths": paths,
            "note": "Suggestions only. No agent execution or build is performed."}

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task")
    args = parser.parse_args()
    print(json.dumps(route(args.task), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
