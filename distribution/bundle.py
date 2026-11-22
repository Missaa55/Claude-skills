"""Independent versioned ZIPs with exact manifests. No network or installers to execute."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile
from distribution.installer import MODULES, ROOT, VERSION, checked_target, is_link

MAX_BYTES = 32_000_000


def _path(name):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name or "\x00" in name:
        raise ValueError("Unsafe package path")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("", ".", "..") for part in name.split("/")):
        raise ValueError("Unsafe package path")
    return name


def payload(module, root=ROOT):
    if module not in MODULES:
        raise ValueError("Unknown module")
    entries = {}
    directories = ["core", "quality", MODULES[module]]
    if module in ("web", "app"):
        directories.append("builders/templates/" + module)
    if module == "web":
        directories.append("builders/templates/footwear")
    for directory in directories:
        base = checked_target(root / directory)
        for path in sorted(base.rglob("*")):
            if is_link(path):
                raise ValueError("Linked package source rejected")
            if path.is_file() and not any(part in {"__pycache__", "dist", "build"} for part in path.relative_to(base).parts) and path.suffix != ".pyc":
                entries[path.relative_to(root).as_posix()] = path.read_bytes()
    for rel in ("builders/__init__.py", "builders/scaffold.py", "distribution/__init__.py", "distribution/cli.py", "distribution/installer.py", "distribution/bundle.py", "LICENSE", f"examples/briefs/{module}.json"):
        path = checked_target(root / rel)
        entries[rel] = path.read_bytes()
    readme = str(Path(MODULES[module]).parent / "README.md").replace("\\", "/")
    entries[readme] = checked_target(root / readme).read_bytes()
    if module == "minecraft":
        entries["Minecraft/COMPATIBILITY.md"] = checked_target(root / "Minecraft/COMPATIBILITY.md").read_bytes()
    if module == "web":
        for rel in ("builders/designer.py", "builders/research.py", "examples/research/electrical-candidates.json", "examples/research/footwear-candidates.json"):
            entries[rel] = checked_target(root / rel).read_bytes()
    entries["builder.py"] = b"import sys\nsys.dont_write_bytecode = True\nfrom core.builder_cli import main\nraise SystemExit(main())\n"
    entries["bundle.json"] = (json.dumps({"builder": module, "version": VERSION}) + "\n").encode()
    entries["BUNDLE_README.txt"] = f"""Claude Skills {module} builder {VERSION}
Requires Python 3.11+. No other builder or repository checkout is required.

Verify before use: python -m distribution.bundle verify .
Install Claude skills: python -m distribution.cli install {module}
Install Codex skills: python -m distribution.cli install {module} --client codex
Use a temporary --target DIRECTORY to review the installation first.
Create reference: python builder.py create --spec examples/briefs/{module}.json --workspace ../new-{module}-project
Review code, then check: python builder.py check {module} --workspace ../new-{module}-project --execute --trusted-local
Cleaner: python builder.py clean {module} --workspace ../new-{module}-project
Update skills: python -m distribution.cli update {module}
Remove skills: python -m distribution.cli uninstall {module}
Status/integrity: python -m distribution.cli status

Creation uses deterministic reference templates, not an authenticated AI run.
Minecraft requires Java 21 and Gradle 8.14.3. Compile/run via the Linux CI workflow.
Web: python build.py; python server.py --port 8080
App: python build.py; python server.py init --demo; python server.py serve --port 8787
Run these project commands from the generated project directory. Demo credentials
are generated once on initialization; there is no default password or real data.
Untrusted AI/code execution requires a separately prepared digest-pinned Docker
image; no host fallback. Authenticated provider-container execution is NOT VERIFIED.
Host execution is for reviewed code only and is not a security sandbox.
No deployment, game EULA acceptance, user-file deletion or cleanup is automatic.
Manifests detect corruption; they are not publisher signatures.
""".encode()
    entries["CHECKSUMS.json"] = (json.dumps({"schema_version": 1, "version": VERSION,
        "builder": module, "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(entries.items())}}, indent=2) + "\n").encode()
    return entries


def build(module: str, output: Path, *, root: Path = ROOT) -> dict:
    if module == "claude-image-studio":
        return build_image_skill(output, root=root)
    output = checked_target(output)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"claude-skills-{module}-{VERSION}.zip"
    entries = payload(module, root)
    with path.open("xb") as stream, zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(_path(name), date_time=(2026, 11, 22, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (output / (path.name + ".sha256")).write_text(digest + "  " + path.name + "\n", encoding="utf-8")
    return {"module": module, "version": VERSION, "archive": str(path), "sha256": digest, "files": len(entries)}


def build_image_skill(output: Path, *, root: Path = ROOT) -> dict:
    output = checked_target(output)
    output.mkdir(parents=True, exist_ok=True)
    base = checked_target(root / "WebBuilder/skills/claude-image-studio")
    entries = {}
    for path in sorted(base.rglob("*")):
        if is_link(path):
            raise ValueError("Linked skill resource rejected")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            entries[path.relative_to(base).as_posix()] = path.read_bytes()
    entries["LICENSE"] = (root / "LICENSE").read_bytes()
    entries["CHECKSUMS.json"] = (json.dumps({"schema_version": 1, "builder": "web", "skill": "claude-image-studio", "version": VERSION,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in sorted(entries.items())}}, indent=2) + "\n").encode()
    path = output / f"claude-image-studio-{VERSION}.zip"
    with path.open("xb") as stream, zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo("claude-image-studio/" + _path(name), date_time=(2026, 11, 22, 0, 0, 0))
            info.compress_type, info.external_attr = zipfile.ZIP_DEFLATED, 0o100644 << 16
            archive.writestr(info, data)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (output / (path.name + ".sha256")).write_text(digest + "  " + path.name + "\n", encoding="utf-8")
    return {"module": "claude-image-studio", "version": VERSION, "archive": str(path), "sha256": digest, "files": len(entries)}


def verify_archive(data: bytes) -> dict[str, bytes]:
    if len(data) > MAX_BYTES:
        raise ValueError("Oversized archive")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            items = archive.infolist()
            if len(items) > 1000 or sum(item.file_size for item in items) > MAX_BYTES:
                raise ValueError("Oversized package contents")
            entries, aliases = {}, set()
            for item in items:
                _path(item.filename)
                if item.filename.casefold() in aliases or stat.S_ISLNK(item.external_attr >> 16) or item.is_dir():
                    raise ValueError("Duplicate, linked or noncanonical archive member")
                aliases.add(item.filename.casefold())
                entries[item.filename] = archive.read(item)
    except zipfile.BadZipFile as exc:
        raise ValueError("Interrupted or corrupt ZIP") from exc
    _verify_entries(entries)
    return entries


def _verify_entries(entries):
    data = json.loads(entries["CHECKSUMS.json"])
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("files"), dict):
        raise ValueError("Invalid package manifest")
    if set(entries) != set(data["files"]) | {"CHECKSUMS.json"}:
        raise ValueError("Missing or unexpected package files")
    for name, digest in data["files"].items():
        _path(name)
        if hashlib.sha256(entries[name]).hexdigest() != digest:
            raise ValueError("Package integrity mismatch: " + name)
    return data


def verify_directory(directory: Path) -> dict:
    directory = checked_target(directory)
    entries = {}
    for path in directory.rglob("*"):
        if is_link(path):
            raise ValueError("Linked package member")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            if path.stat().st_size > MAX_BYTES:
                raise ValueError("Oversized package member")
            entries[path.relative_to(directory).as_posix()] = path.read_bytes()
    data = _verify_entries(entries)
    return {"status": "integrity_verified", "builder": data["builder"], "version": data["version"], "files": len(entries)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("build")
    cmd.add_argument("module", choices=[*MODULES, "claude-image-studio", "all"])
    cmd.add_argument("--output", type=Path, required=True)
    cmd = sub.add_parser("verify")
    cmd.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        result = [build(module, args.output) for module in [*MODULES, "claude-image-studio"]] if args.command == "build" and args.module == "all" else build(args.module, args.output) if args.command == "build" else verify_directory(args.directory)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
