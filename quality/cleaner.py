"""Read-only AI-slop heuristics and safe cleanup candidate detection.

No files are deleted or rewritten. Findings are suggestions, not proof of AI origin.
"""
from pathlib import Path
import argparse
import json
import re

BUILDER_RULES = {
    "web": {"extensions": {".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".md"},
            "slop": ("lorem ipsum", "your amazing journey", "unleash the power", "revolutionize your")},
    "app": {"extensions": {".py", ".js", ".jsx", ".ts", ".tsx", ".md"},
            "slop": ("lorem ipsum", "todo: implement", "replace with your api key", "your amazing journey")},
    "minecraft": {"extensions": {".java", ".kt", ".json", ".mcfunction", ".md"},
                  "slop": ("todo: implement", "examplemod", "replace with your mod id", "lorem ipsum")},
}
CANDIDATE_NAMES = {".ds_store", "thumbs.db"}
CANDIDATE_SUFFIXES = {".tmp", ".bak", ".orig"}
PROTECTED_SEGMENTS = {".git", ".github", "node_modules", ".gradle", "build", "dist",
                      "target", "migrations", "assets", "resources", "data",
                      "world", "world_nether", "world_the_end", ".minecraft",
                      ".claude-skills", ".venv", "venv", "saves"}
MAX_FILE_BYTES = 256_000

def scan(root: Path, builder: str) -> dict:
    if builder not in BUILDER_RULES:
        raise ValueError("Unsupported builder")
    root = root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Root must be a directory")
    findings = []
    visited = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part.casefold() in PROTECTED_SEGMENTS for part in relative.parts[:-1]):
            continue
        visited += 1
        name = path.name.casefold()
        if name in CANDIDATE_NAMES or path.suffix.casefold() in CANDIDATE_SUFFIXES:
            findings.append({"path": relative.as_posix(), "kind": "cleanup_candidate",
                             "severity": "review", "reason": "Likely temporary or backup artifact; verify before deletion"})
        if path.suffix.casefold() not in BUILDER_RULES[builder]["extensions"]:
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            content = path.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            continue
        for phrase in BUILDER_RULES[builder]["slop"]:
            if re.search(r"(?i)(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", content):
                findings.append({"path": relative.as_posix(), "kind": "slop_candidate",
                                 "severity": "review", "reason": f"Review generic or placeholder text: {phrase}"})
    return {"builder": builder, "root": str(root), "scanned_files": visited,
            "findings": findings, "deleted_files": 0,
            "notice": "Heuristic review only. No files were changed or deleted."}

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("builder", choices=sorted(BUILDER_RULES))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = scan(args.directory, args.builder)
    content = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        if args.output.exists():
            parser.error("Output exists; refusing overwrite")
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")

if __name__ == "__main__":
    main()
