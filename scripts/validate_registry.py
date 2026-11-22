#!/usr/bin/env python3
"""Check that every registered skill and cross-domain reference actually exists."""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "framework" / "registry.json"
SKILL_DIRS = ("skills", "Minecraft/skills", "Universal/skills",
              "Applications/skills", "AppBuilder/skills", "WebBuilder/skills")
REFERENCE = re.compile(r"(?:Minecraft|Universal|Applications|AppBuilder|WebBuilder)/skills/[a-z0-9-]+/SKILL\.md")

def check_registry(root: Path = ROOT, registry: dict | None = None) -> list[str]:
    errors = []
    if registry is None:
        try:
            registry = json.loads((root / "framework/registry.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return [f"Invalid registry: {exc}"]
    domains = registry.get("domains", {})
    if not isinstance(domains, dict) or not domains:
        return ["Missing domains"]
    seen = set()
    for domain, config in domains.items():
        prefix = config.get("root", "")
        skills = config.get("skills", [])
        if prefix not in SKILL_DIRS:
            errors.append(f"{domain}: unknown skill root {prefix}")
            continue
        if len(skills) != len(set(skills)):
            errors.append(f"{domain}: duplicate skills")
        if not set(config.get("default", [])).issubset(skills):
            errors.append(f"{domain}: default is not in skills")
        for skill in skills:
            path = f"{prefix}/{skill}/SKILL.md"
            if path in seen:
                errors.append(f"Duplicate registered path: {path}")
            seen.add(path)
            if not (root / path).is_file():
                errors.append(f"Missing registered skill: {path}")
    shared = registry.get("shared_skills", [])
    for skill in shared:
        path = f"skills/{skill}/SKILL.md"
        seen.add(path)
        if not (root / path).is_file():
            errors.append(f"Missing shared skill: {path}")
    for key in registry.get("shared_skill_keywords", {}):
        if key not in shared:
            errors.append(f"Unknown shared alias target: {key}")
    for key in registry.get("skill_keywords", {}):
        if "/" in key:
            domain, skill = key.split("/", 1)
            if domain not in domains or skill not in domains[domain].get("skills", []):
                errors.append(f"Unknown skill alias target: {key}")
        elif not any(key in cfg.get("skills", []) for cfg in domains.values()):
            errors.append(f"Unknown skill alias target: {key}")
    for directory in SKILL_DIRS:
        for path in (root / directory).glob("*/SKILL.md"):
            rel = path.relative_to(root).as_posix()
            if rel not in seen:
                errors.append(f"Unregistered skill: {rel}")
    # Check canonical references in the cooperation document.
    cooperation = root / "WebBuilder/COOPERATION.md"
    if cooperation.is_file():
        for ref in REFERENCE.findall(cooperation.read_text(encoding="utf-8")):
            if not (root / ref).is_file():
                errors.append(f"Broken cooperation reference: {ref}")
    for name in ("task.schema.json", "review.schema.json"):
        path = root / "AppBuilder/contracts" / name
        if not path.is_file():
            errors.append(f"Missing contract: {path.relative_to(root)}")
        else:
            try:
                schema = json.loads(path.read_text(encoding="utf-8"))
                if schema.get("type") != "object" or not schema.get("properties"):
                    errors.append(f"Invalid contract shape: {name}")
            except ValueError:
                errors.append(f"Invalid JSON contract: {name}")
    return errors

def main() -> int:
    errors = check_registry()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Registry, aliases, paths and contracts validated")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
