"""Quality Cleaner V2: bounded, read-only analysis. No AI-origin claims or deletion."""
import argparse
import ast
import difflib
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import stat
import sys

BUILDER_RULES = {
    "web": {"slop": ("lorem ipsum", "your amazing journey", "unleash the power", "revolutionize your")},
    "app": {"slop": ("lorem ipsum", "todo: implement", "replace with your api key", "your amazing journey")},
    "minecraft": {"slop": ("todo: implement", "examplemod", "replace with your mod id", "lorem ipsum")},
}
IGNORED = {".git", "node_modules", ".gradle", "build", "dist", "target", "world", "world_nether",
           "world_the_end", ".minecraft", ".claude-skills", ".venv", "venv", "saves", "__pycache__", ".tools", ".artifacts"}
PROTECTED_SEGMENTS = IGNORED | {".github", "migrations", "assets", "resources", "data"}
TEXT_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".json", ".mcfunction", ".md", ".html", ".css", ".toml", ".sql", ".yml", ".yaml", ".gradle", ".mcmeta"}
MAX_FILE_BYTES, MAX_FILES, MAX_TOTAL_BYTES = 256_000, 5000, 16_000_000


def _linked(path):
    try:
        info = path.lstat()
        return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)
    except OSError:
        return True


def _inventory(root):
    files, contents, skipped, total = {}, {}, [], 0
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d.casefold() not in IGNORED and not _linked(Path(directory) / d))
        for name in sorted(names):
            path = Path(directory) / name
            rel = path.relative_to(root).as_posix()
            if _linked(path) or not path.is_file() or name.startswith(".env"):
                continue
            if len(files) >= MAX_FILES:
                return files, contents, skipped + ["File-count limit reached"]
            files[rel] = path
            if path.suffix not in TEXT_EXTENSIONS:
                continue
            size = path.stat().st_size
            if size > MAX_FILE_BYTES or total + size > MAX_TOTAL_BYTES:
                skipped.append(rel)
                continue
            total += size
            try:
                contents[rel] = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                skipped.append(rel)
    return files, contents, skipped


def _finding(findings, path, kind, reason, line=None, severity="review", confidence="heuristic"):
    item = {"path": path, "kind": kind, "severity": severity, "reason": reason, "confidence": confidence}
    if line:
        item["line"] = line
    findings.append(item)


def _python(path, content, findings, functions):
    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        _finding(findings, path, "syntax_error", "Python parser rejected this file", exc.lineno, "error", "static")
        return
    loaded = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    exports = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets):
            if isinstance(n.value, (ast.List, ast.Tuple)):
                exports.update(v.value for v in n.value.elts if isinstance(v, ast.Constant) and isinstance(v.value, str))
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)) and not path.endswith("__init__.py"):
            for alias in n.names:
                name = alias.asname or (alias.name.split(".")[0] if isinstance(n, ast.Import) else alias.name)
                if name != "*" and name not in loaded | exports:
                    _finding(findings, path, "unused_import_candidate", f"No static load of imported name {name}; check dynamic use and import side effects", n.lineno)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body = ast.dump(ast.Module(body=n.body, type_ignores=[]), include_attributes=False)
            if len(body) > 350 and len(n.body) >= 3:
                functions.setdefault(body, []).append((path, n.lineno))
        for _, value in ast.iter_fields(n):
            if isinstance(value, list) and value and all(isinstance(v, ast.stmt) for v in value):
                for i, statement in enumerate(value[:-1]):
                    if isinstance(statement, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                        _finding(findings, path, "unreachable_code", "Statement follows an unconditional control transfer in the same block", value[i+1].lineno, "warning", "static")
                        break
        if isinstance(n, ast.If) and isinstance(n.test, ast.Constant) and n.test.value is False and n.body:
            _finding(findings, path, "unreachable_code", "Literal if False block", n.lineno, "warning", "static")
    names = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_")]
    if any("_" in n for n in names) and any(re.search(r"[a-z][A-Z]", n) for n in names):
        _finding(findings, path, "naming_candidate", "Public Python functions mix snake_case and camelCase; check project convention")


class _HTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.language, self.viewport = False, False
        self.images, self.references, self.labels, self.inputs = [], [], set(), []
    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "html": self.language = bool(data.get("lang"))
        if tag == "meta" and data.get("name") == "viewport": self.viewport = True
        if tag == "img" and "alt" not in data: self.images.append(self.getpos()[0])
        for attr in ("src", "href"):
            if data.get(attr): self.references.append(data[attr])
        if tag == "label" and data.get("for"): self.labels.add(data["for"])


def _web(path, content, findings):
    if path.endswith(".html"):
        parser = _HTML()
        try:
            parser.feed(content)
        except ValueError:
            return
        if not parser.language: _finding(findings, path, "accessibility", "Missing document language", severity="warning", confidence="static")
        if not parser.viewport: _finding(findings, path, "responsive", "Missing viewport metadata", severity="warning", confidence="static")
        for line in parser.images: _finding(findings, path, "accessibility", "Image lacks alt attribute", line, "warning", "static")
        if not re.search(r"<title>\s*[^<]+", content, re.I): _finding(findings, path, "seo", "Missing document title", severity="warning", confidence="static")
    if path.endswith(".css") and content.count("linear-gradient(") >= 4 and content.count("box-shadow") >= 4:
        _finding(findings, path, "visual_pattern_candidate", "Repeated gradients and shadows warrant screenshot review; this does not establish poor design or AI origin")


def _references(contents, files, findings):
    incoming = set()
    all_text = "\n".join(contents.values())
    for rel, content in contents.items():
        refs = []
        if rel.endswith(".html"):
            parser = _HTML()
            parser.feed(content)
            refs.extend(parser.references)
        refs.extend(re.findall(r'(?:from\s*|require\s*\(|import\s*\(|url\s*\()\s*[\"\']([^\"\']+)[\"\']', content))
        for value in refs:
            value = value.split("#")[0].split("?")[0]
            if not value or ":" in value or value.startswith("//"):
                continue
            candidate = (Path(rel).parent / value).as_posix() if not value.startswith("/") else value[1:]
            candidate = os.path.normpath(candidate).replace("\\", "/")
            choices = [candidate, *(candidate + ext for ext in (".js", ".ts", ".tsx", ".jsx")), candidate + "/index.js"]
            incoming.update(choice for choice in choices if choice in files)
    for rel in files:
        path = Path(rel)
        if path.suffix not in {".js", ".jsx", ".ts", ".tsx"} or rel in incoming:
            continue
        if path.stem in {"index", "main", "app", "site", "server", "service-worker"} or any(v in path.parts for v in ("tests", "test", "scripts")) or ".config." in rel or re.search(r"\.(test|spec)\.", rel):
            continue
        if path.name not in all_text:
            _finding(findings, rel, "unused_file_candidate", "No incoming literal import/HTML/CSS reference found; dynamic loaders and framework conventions remain unverified")
    for rel, content in contents.items():
        if Path(rel).name == "package.json":
            try:
                package = json.loads(content)
                deps = package.get("dependencies", {})
                scripts = " ".join(package.get("scripts", {}).values())
                sources = "\n".join(value for key, value in contents.items() if key != rel)
                for name in deps:
                    if name not in sources and name not in scripts:
                        _finding(findings, rel, "dependency_candidate", f"No literal reference to dependency {name}; check plugins and dynamic resolution")
            except (ValueError, AttributeError, TypeError):
                _finding(findings, rel, "invalid_manifest", "Cannot parse package dependency manifest", severity="error", confidence="static")


def _minecraft(contents, files, findings):
    for rel, content in contents.items():
        if not rel.endswith((".json", ".mcmeta")):
            continue
        try:
            data = json.loads(content)
        except ValueError:
            _finding(findings, rel, "invalid_json", "Minecraft JSON did not parse", severity="error", confidence="static")
            continue
        if not isinstance(data, dict):
            continue
        if rel.endswith("fabric.mod.json"):
            if data.get("depends", {}).get("minecraft") in (None, "*"):
                _finding(findings, rel, "version_candidate", "Minecraft compatibility is unspecified or unrestricted")
            for entry in data.get("entrypoints", {}).get("main", []):
                if isinstance(entry, str) and not any(path.endswith(entry.replace(".", "/") + ".java") or path.endswith(entry.replace(".", "/") + ".kt") for path in files):
                    _finding(findings, rel, "registration", "Fabric main entrypoint source was not found", severity="warning", confidence="static")
        if "/models/" in rel and "/assets/" in rel:
            prefix = rel.split("/assets/")[0] + "/assets/"
            for value in data.get("textures", {}).values():
                if not isinstance(value, str) or value.startswith("#") or ":" not in value:
                    continue
                namespace, texture = value.split(":", 1)
                if namespace != "minecraft" and prefix + namespace + "/textures/" + texture + ".png" not in files:
                    _finding(findings, rel, "missing_asset", f"Local texture reference is missing: {namespace}:{texture}", severity="error", confidence="static")
        if "/recipe/" in rel:
            if not isinstance(data.get("type"), str) or not isinstance(data.get("result"), (str, dict)):
                _finding(findings, rel, "recipe", "Recipe lacks a type or result; validate against the chosen game version", severity="error", confidence="static")


def scan(root: Path, builder: str) -> dict:
    if builder not in BUILDER_RULES:
        raise ValueError("Unsupported builder")
    root = Path(os.path.abspath(root.expanduser()))
    if sys.platform == "darwin":
        for alias in (Path("/var"), Path("/tmp"), Path("/etc")):
            expected = Path("/private") / alias.name
            if root.is_relative_to(alias) and alias.is_symlink() and alias.lstat().st_uid == 0 and alias.resolve() == expected:
                root = expected / root.relative_to(alias)
                break
    if not root.is_dir() or any(_linked(p) for p in (root, *root.parents)):
        raise ValueError("Root must be an unlinked directory")
    files, contents, skipped = _inventory(root)
    findings, functions, duplicates = [], {}, {}
    for rel, path in files.items():
        protected = any(part.casefold() in PROTECTED_SEGMENTS for part in Path(rel).parts[:-1])
        if not protected and (path.name.casefold() in {".ds_store", "thumbs.db"} or path.suffix.casefold() in {".tmp", ".bak", ".orig"}):
            _finding(findings, rel, "cleanup_candidate", "Backup or temporary filename; verify ownership and references before proposing removal")
    for rel, content in contents.items():
        matched_todo = False
        for phrase in BUILDER_RULES[builder]["slop"]:
            match = re.search(r"(?i)(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", content)
            if match:
                _finding(findings, rel, "slop_candidate", f"Review generic or placeholder wording: {phrase}; no inference about authorship", content.count("\n", 0, match.start()) + 1)
                matched_todo |= "todo" in phrase
        if not matched_todo:
            for match in re.finditer(r"\b(?:TODO|FIXME)\b", content):
                _finding(findings, rel, "unfinished_work", "TODO/FIXME requires an explicit disposition", content.count("\n", 0, match.start()) + 1)
        if re.search(r"\b(?:eval|exec)\s*\(|shell\s*=\s*True|dangerously-bypass", content):
            _finding(findings, rel, "security_candidate", "Dynamic execution, shell mode or permission bypass requires manual review", severity="warning")
        if re.search(r"\b(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,})\b|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", content):
            _finding(findings, rel, "credential_candidate", "Possible embedded credential; value deliberately omitted", severity="error")
        if len(content.strip()) > 300:
            duplicates.setdefault(hashlib.sha256(content.strip().encode()).hexdigest(), []).append(rel)
        if rel.endswith(".py"):
            _python(rel, content, findings, functions)
        if builder == "web":
            _web(rel, content, findings)
        # A browser fetch client does not implement server authentication. Limit this
        # heuristic to recognizable route definitions; external middleware still
        # requires manual tracing and is never certified by a literal marker.
        server_route = re.search(r"def do_(?:GET|POST|PUT|PATCH|DELETE)\b|(?:app|router)\.(?:get|post|put|patch|delete|route)\s*\(|@(?:Get|Post|Put|Patch|Delete)Mapping|export\s+(?:async\s+)?function\s+(?:GET|POST|PUT|PATCH|DELETE)\b", content)
        if builder == "app" and len(content) > 500 and "/api/" in content and server_route:
            if not re.search(r"session|auth|jwt", content, re.I):
                _finding(findings, rel, "api_auth_candidate", "API source has no literal authentication/session marker; trace actual middleware", severity="warning")
            if not re.search(r"valid|422|isinstance|zod|pydantic", content, re.I):
                _finding(findings, rel, "api_validation_candidate", "API source has no recognizable input-validation marker; inspect contracts", severity="warning")
    for group in functions.values():
        for path, line in group[1:]:
            _finding(findings, path, "duplicate_code_candidate", f"Normalized function body repeats {group[0][0]}:{group[0][1]}; assess intentional duplication", line)
    for group in duplicates.values():
        for path in group[1:]:
            _finding(findings, path, "duplicate_file_candidate", f"Text matches {group[0]}; generated assets may intentionally match")
    _references(contents, files, findings)
    if builder == "minecraft":
        _minecraft(contents, files, findings)
    source = [p for p in contents if Path(p).suffix in {".py", ".java", ".js", ".ts", ".tsx"} and len(contents[p]) > 500]
    if source and not any("test" in p.casefold() or "spec." in p for p in files):
        _finding(findings, ".", "missing_tests_candidate", "No test-like paths found; external tests and framework conventions remain unverified", severity="warning")
    return {"schema_version": 2, "builder": builder, "root": str(root), "scanned_files": len(files),
            "findings": sorted(findings, key=lambda f: (f["path"], f.get("line", 0), f["kind"])),
            "skipped": skipped, "deleted_files": 0, "modified_files": 0,
            "visual_review": "NOT VERIFIED; use browser screenshots and accessibility tests" if builder == "web" else "not_applicable",
            "limitations": ["Python AST checks are static; JS imports and dependency references are conservative heuristics",
                            "Dynamic imports, framework entrypoints and security cannot be proved from this scan",
                            "Minecraft asset/recipe checks do not establish in-game registration"],
            "notice": "Read-only findings and stylistic suspicions. No proof of AI origin. No files changed or deleted."}


def proposal(root: Path, builder: str) -> dict:
    report = scan(root, builder)
    root = Path(report["root"])
    changes = []
    for rel in sorted({f["path"] for f in report["findings"] if f["kind"] == "unused_import_candidate"}):
        path = root / rel
        before = path.read_text(encoding="utf-8")
        lines = before.splitlines(keepends=True)
        remove = {f["line"] for f in report["findings"] if f["path"] == rel and f["kind"] == "unused_import_candidate"}
        # Propose only complete single-name module imports, never imports with side
        # comments, aliases with a shared line, from imports, or import-time annotations.
        remove = {n for n in remove if re.fullmatch(r"import [A-Za-z_][\w.]*(?: as [A-Za-z_]\w*)?\s*", lines[n-1])}
        after = "".join(line for n, line in enumerate(lines, 1) if n not in remove)
        if after != before:
            changes.append({"path": rel, "before_sha256": hashlib.sha256(before.encode()).hexdigest(),
                            "after_sha256": hashlib.sha256(after.encode()).hexdigest(),
                            "reason": "No static uses; review dynamic behavior and import side effects before applying",
                            "diff": "".join(difflib.unified_diff(lines, after.splitlines(keepends=True), fromfile="a/"+rel, tofile="b/"+rel, n=0))})
    return {"status": "proposal_only", "changes": changes, "applied": False,
            "rollback": "Review and save each diff; after separately approved application, git apply --reverse <patch> restores it. Verify hashes first."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("builder", choices=sorted(BUILDER_RULES))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--proposal", action="store_true", help="Produce reviewable diffs only; never applies them")
    args = parser.parse_args()
    report = proposal(args.directory, args.builder) if args.proposal else scan(args.directory, args.builder)
    content = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(content)
    else:
        print(content, end="")


if __name__ == "__main__":
    main()
