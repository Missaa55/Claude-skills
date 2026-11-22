"""Install only the selected builder's skills into a local Claude Code directory.

No network requests, subprocesses, provider authentication or model execution.
"""
from pathlib import Path
import hashlib
import json
import os
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MODULES = {
    "minecraft": "Minecraft/skills",
    "app": "AppBuilder/skills",
    "web": "WebBuilder/skills",
}
STATE = ".claude-skills-install.json"

def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _source_files(module: str, root: Path) -> dict[str, bytes]:
    if module not in MODULES:
        raise ValueError(f"Unknown module: {module}")
    base = root / MODULES[module]
    if not base.is_dir():
        raise FileNotFoundError(base)
    files = {}
    for skill in sorted(base.iterdir()):
        if not skill.is_dir() or skill.is_symlink():
            continue
        for file in sorted(skill.rglob("*")):
            if file.is_symlink():
                raise ValueError(f"Symlinks are not supported: {file}")
            if file.is_file():
                rel = file.relative_to(base).as_posix()
                files[rel] = file.read_bytes()
    if not files or not any(p.endswith("/SKILL.md") for p in files):
        raise ValueError("Module has no skills")
    # Ship the working read-only cleaner INSIDE the selected builder's skill.
    # A single-module install must not require the rest of this repository.
    cleaner_skill = {"minecraft": "minecraft-quality-cleaner",
                     "app": "appbuilder-quality-cleaner",
                     "web": "webbuilder-quality-cleaner"}[module]
    source = root / "quality" / "cleaner.py"
    if source.is_symlink() or not source.is_file():
        raise FileNotFoundError(f"Missing standalone cleaner: {source}")
    rel = f"{cleaner_skill}/scripts/cleaner.py"
    files[rel] = source.read_bytes()
    return files

def _state(target: Path) -> dict:
    path = target / STATE
    if not path.exists():
        return {"schema_version": 1, "modules": {}}
    if path.is_symlink():
        raise ValueError("State file must not be a symlink")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("modules"), dict):
        raise ValueError("Unsupported installation state")
    return data

def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".install-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def _destination(target: Path, name: str) -> Path:
    # State is JSON on disk, therefore treat its paths as untrusted input.
    # Reject traversal and absolute paths before any read, write or deletion.
    parts = Path(name)
    if (parts.is_absolute() or not parts.parts or
            any(part in (".", "..") for part in parts.parts) or
            "\\\\" in name or ":" in name or name.startswith(("/", "\\\\"))):
        raise ValueError(f"Unsafe installation path: {name}")
    dest = target / parts
    if dest.is_symlink() or any(p.is_symlink() for p in list(dest.parents) if p != target and target in p.parents):
        raise ValueError(f"Symlink destination rejected: {dest}")
    return dest

def install(module: str, target: Path, *, root: Path = ROOT) -> dict:
    files = _source_files(module, root)
    target = target.expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    state = _state(target)
    existing = state["modules"].get(module, {})
    previous = existing.get("files", {})
    planned = {}
    for rel, content in files.items():
        dest = _destination(target, rel)
        digest = _digest(content)
        if dest.exists():
            if not dest.is_file():
                raise FileExistsError(dest)
            current = _digest(dest.read_bytes())
            if current != digest and current != previous.get(rel):
                raise FileExistsError(f"Refusing to overwrite modified or unmanaged file: {dest}")
        planned[rel] = digest
    for rel in previous:
        if rel not in planned:
            dest = _destination(target, rel)
            if dest.exists() and _digest(dest.read_bytes()) != previous[rel]:
                raise FileExistsError(f"Refusing to delete modified file: {dest}")
    for rel, content in files.items():
        _write_atomic(_destination(target, rel), content)
    for rel in previous:
        if rel not in planned:
            _destination(target, rel).unlink(missing_ok=True)
    state["modules"][module] = {"files": planned}
    _write_atomic(target / STATE, (json.dumps(state, indent=2, sort_keys=True) + "\n").encode())
    return {"module": module, "files": len(planned), "target": str(target)}

def uninstall(module: str, target: Path) -> dict:
    if module not in MODULES:
        raise ValueError(f"Unknown module: {module}")
    target = target.expanduser().resolve()
    state = _state(target)
    record = state["modules"].get(module)
    if record is None:
        return {"module": module, "removed": 0}
    files = record["files"]
    for rel, digest in files.items():
        dest = _destination(target, rel)
        if dest.exists() and (not dest.is_file() or _digest(dest.read_bytes()) != digest):
            raise FileExistsError(f"Refusing to delete modified file: {dest}")
    for rel in files:
        dest = _destination(target, rel)
        dest.unlink(missing_ok=True)
        parent = dest.parent
        while parent != target and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
    del state["modules"][module]
    if state["modules"]:
        _write_atomic(target / STATE, (json.dumps(state, indent=2, sort_keys=True) + "\n").encode())
    else:
        # Do not leave our state file behind after removing the final module.
        (target / STATE).unlink(missing_ok=True)
    return {"module": module, "removed": len(files)}

def status(target: Path) -> dict:
    state = _state(target.expanduser().resolve())
    return {"installed": sorted(state["modules"])}
