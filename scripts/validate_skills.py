#!/usr/bin/env python3
"""Minimal standard-library validation for SKILL.md files."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
REQUIRED = ("## When to use", "## Procedure", "## Output")
SLUG = re.compile(r"^[a-z][a-z0-9-]*$")
FIELD = re.compile(r"^(name|description):\s*(.+)$", re.MULTILINE)
SUSPICIOUS = re.compile(
    r"(?i)(?:-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|"
    r"\b(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b)"
)


def validate(path: Path) -> list[str]:
    errors = []
    if not SLUG.fullmatch(path.parent.name):
        errors.append(f"{path}: invalid directory slug")
    body = path.read_text(encoding="utf-8")
    if not body.startswith("---\n"):
        return errors + [f"{path}: missing YAML frontmatter"]
    parts = body.split("---\n", 2)
    if len(parts) < 3:
        return errors + [f"{path}: unclosed YAML frontmatter"]
    metadata = dict(FIELD.findall(parts[1]))
    if metadata.get("name") != path.parent.name:
        errors.append(f"{path}: name must match directory")
    if not metadata.get("description", "").strip():
        errors.append(f"{path}: missing description")
    for heading in REQUIRED:
        if heading not in parts[2]:
            errors.append(f"{path}: missing {heading}")
    if SUSPICIOUS.search(body):
        errors.append(f"{path}: potential credential detected")
    return errors


def main() -> int:
    paths = sorted(path for domain in ("skills", "Minecraft/skills", "Universal/skills", "Applications/skills", "AppBuilder/skills", "WebBuilder/skills") for path in (ROOT / domain).glob("*/SKILL.md"))
    if not paths:
        print("No skills found", file=sys.stderr)
        return 1
    errors = [error for path in paths for error in validate(path)]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Validated {len(paths)} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
