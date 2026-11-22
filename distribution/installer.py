"""Offline journalled lifecycle; refuses links, foreign ownership and user edits."""
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
import base64
import hashlib
import json
import os
import re
import stat
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.2.0"
MODULES = {"minecraft": "Minecraft/skills", "app": "AppBuilder/skills", "web": "WebBuilder/skills"}
OWNED_SKILLS = {
    "minecraft": {"minecraft-architecture", "minecraft-ai-integration", "minecraft-assets", "minecraft-datapack", "minecraft-fabric", "minecraft-neoforge", "minecraft-paper", "minecraft-quality-cleaner", "minecraft-release", "minecraft-server-ops", "minecraft-testing", "minecraft-worldgen"},
    "app": {"appbuilder-orchestrator", "appbuilder-design", "appbuilder-quality", "appbuilder-quality-cleaner"},
    "web": {"webbuilder-orchestrator", "webbuilder-research", "webbuilder-design-system", "webbuilder-layout", "webbuilder-content-seo", "webbuilder-accessibility", "webbuilder-performance", "webbuilder-visual-qa", "webbuilder-security", "webbuilder-publishing", "webbuilder-cms", "webbuilder-integration", "webbuilder-quality-cleaner", "claude-image-studio"},
}
STATE = ".claude-skills-install.json"
JOURNAL = ".claude-skills-transaction.json"
LOCK = ".claude-skills-lock"
MAX_STATE, MAX_JOURNAL = 8_000_000, 32_000_000


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_link(path: Path) -> bool:
    """Also detects Windows junctions and dangling reparse points."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def checked_target(target: Path) -> Path:
    target = Path(os.path.abspath(target.expanduser()))
    # macOS exposes its OS-owned /private trees through these exact aliases.
    # Normalize only verified root-owned system links, never arbitrary user links.
    if sys.platform == "darwin":
        for alias in (Path("/var"), Path("/tmp"), Path("/etc")):
            expected = Path("/private") / alias.name
            if target.is_relative_to(alias) and alias.is_symlink() and alias.lstat().st_uid == 0 and alias.resolve() == expected:
                target = expected / target.relative_to(alias)
                break
    for part in [*reversed(target.parents), target]:
        if is_link(part):
            raise ValueError(f"Linked path rejected: {part}")
    return target


def _name(name: str, module: str | None = None) -> str:
    if not isinstance(name, str) or not name or len(name) > 240:
        raise ValueError("Invalid installation path")
    parts = name.split("/")
    if any(not p or p in (".", "..") or p[-1:] in (".", " ") or
           re.search(r'[\\:<>"|?*\x00-\x1f]', p) or
           re.fullmatch(r"(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?", p)
           for p in parts):
        raise ValueError(f"Unsafe installation path: {name}")
    if PurePosixPath(name).is_absolute() or len(parts) < 2:
        raise ValueError(f"Unsafe installation path: {name}")
    if module and (module not in OWNED_SKILLS or parts[0] not in OWNED_SKILLS[module]):
        raise ValueError(f"Path does not belong to module {module}: {name}")
    return name


def _destination(target: Path, name: str, module: str | None = None) -> Path:
    _name(name, module)
    dest = target.joinpath(*name.split("/"))
    for part in [dest, *dest.parents]:
        if part == target:
            break
        if is_link(part):
            raise ValueError(f"Linked destination rejected: {part}")
    return dest


def _source_files(module: str, root: Path) -> dict[str, bytes]:
    if module not in MODULES:
        raise ValueError(f"Unknown module: {module}")
    base = checked_target(root / MODULES[module])
    if not base.is_dir():
        raise FileNotFoundError(base)
    files = {}
    for directory, dirs, names in os.walk(base, followlinks=False):
        for name in [*dirs, *names]:
            if is_link(Path(directory) / name):
                raise ValueError("Linked source rejected")
        for name in names:
            file = Path(directory) / name
            if file.suffix == ".pyc" or "__pycache__" in file.parts:
                continue
            rel = file.relative_to(base).as_posix()
            _name(rel, module)
            files[rel] = file.read_bytes()
    if not any(p.endswith("/SKILL.md") for p in files):
        raise ValueError("Module has no skills")
    prefix = {"minecraft": "minecraft", "app": "appbuilder", "web": "webbuilder"}[module]
    source = checked_target(root / "quality/cleaner.py")
    files[f"{prefix}-quality-cleaner/scripts/cleaner.py"] = source.read_bytes()
    # A skills-only install must still have an executable, self-contained builder.
    # payload contains only source skills (never generated installation trees).
    from distribution.bundle import payload
    orchestrator = "minecraft-architecture" if module == "minecraft" else prefix + "-orchestrator"
    for rel, data in payload(module, root).items():
        files[f"{orchestrator}/runtime/{rel}"] = data
    return dict(sorted(files.items()))


def _read_json(path: Path, limit: int) -> dict:
    if is_link(path) or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("Invalid metadata file")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate metadata key")
            result[key] = value
        return result
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    if not isinstance(data, dict):
        raise ValueError("Metadata must be an object")
    return data


def _validate_state(data: dict, target: Path) -> dict:
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("modules"), dict):
        raise ValueError("Unsupported installation state")
    owners = set()
    for module, record in data["modules"].items():
        if module not in MODULES or not isinstance(record, dict) or not isinstance(record.get("files"), dict):
            raise ValueError("Invalid module record")
        for rel, digest in record["files"].items():
            _destination(target, rel, module)
            alias = rel.casefold()
            if alias in owners or not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest):
                raise ValueError("Invalid file ownership or digest")
            owners.add(alias)
    return data


def _state(target: Path) -> dict:
    path = target / STATE
    if is_link(path):
        raise ValueError("State must not be linked")
    if not path.exists():
        return {"schema_version": 1, "modules": {}}
    return _validate_state(_read_json(path, MAX_STATE), target)


def _write_atomic(path: Path, data: bytes) -> None:
    if is_link(path):
        raise ValueError("Linked write rejected")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".install-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


_restore_atomic = _write_atomic


def _json_bytes(data: dict) -> bytes:
    return (json.dumps(data, sort_keys=True, indent=2) + "\n").encode()


def _prune(target: Path, paths) -> None:
    parents = {p for path in paths for p in path.parents if p != target and target in p.parents}
    for parent in sorted(parents, key=lambda p: len(p.parts), reverse=True):
        if parent.is_dir() and not is_link(parent) and not any(parent.iterdir()):
            parent.rmdir()


@contextmanager
def _lock(target: Path):
    target.mkdir(parents=True, exist_ok=True)
    directory = target / LOCK
    try:
        directory.mkdir()
    except FileExistsError:
        raise BlockingIOError("Active or abandoned installation lock; inspect owner and use recover") from None
    try:
        _restore_atomic(directory / "owner.json", _json_bytes({"pid": os.getpid()}))
        yield
    finally:
        (directory / "owner.json").unlink(missing_ok=True)
        directory.rmdir()


def _snapshot(path: Path) -> str | None:
    if not path.exists():
        return None
    if is_link(path) or not path.is_file() or path.stat().st_size > MAX_STATE:
        raise ValueError("Invalid transaction file")
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _decode(value) -> bytes | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Invalid journal data")
    return base64.b64decode(value, validate=True)


def _recover(target: Path) -> bool:
    journal_path = target / JOURNAL
    if not journal_path.exists() and not is_link(journal_path):
        return False
    journal = _read_json(journal_path, MAX_JOURNAL)
    module = journal.get("module")
    if module not in MODULES or journal.get("version") != 1 or not isinstance(journal.get("entries"), dict):
        raise ValueError("Invalid transaction journal")
    operations = []
    for rel, entry in journal["entries"].items():
        path = target / STATE if rel == STATE else _destination(target, rel, module)
        if not isinstance(entry, dict) or set(entry) != {"before", "after"}:
            raise ValueError("Invalid journal entry")
        before, after = _decode(entry["before"]), _decode(entry["after"])
        if rel == STATE:
            for content in (before, after):
                if content is not None:
                    _validate_state(json.loads(content), target)
        if _decode(_snapshot(path)) not in (before, after):
            raise FileExistsError("Recovery would overwrite a subsequent user change")
        operations.append((path, before))
    # The complete journal is validated before restoring any files.
    for path, content in reversed(operations):
        if _decode(_snapshot(path)) == content:
            continue
        if content is None:
            path.unlink(missing_ok=True)
        else:
            _restore_atomic(path, content)
    _prune(target, [p for p, _ in operations])
    journal_path.unlink()
    return True


def recover(target: Path, *, abandoned_lock: bool = False) -> dict:
    target = checked_target(target)
    directory = target / LOCK
    if abandoned_lock and directory.exists():
        if is_link(directory):
            raise ValueError("Linked lock rejected")
        pid = _read_json(directory / "owner.json", 1024).get("pid")
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
            raise ValueError("Invalid lock owner; manual review required")
        if os.name == "nt":
            import ctypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenProcess.restype = ctypes.c_void_p
            handle = kernel.OpenProcess(0x1000, False, pid)
            alive = bool(handle) or ctypes.get_last_error() == 5
            if handle:
                kernel.CloseHandle(ctypes.c_void_p(handle))
        else:
            try:
                os.kill(pid, 0)
                alive = True
            except ProcessLookupError:
                alive = False
            except PermissionError:
                alive = True
        if alive:
            raise BlockingIOError("Lock owner is still alive")
        (directory / "owner.json").unlink()
        directory.rmdir()
    with _lock(target):
        return {"recovered": _recover(target)}


def _transaction(module: str, target: Path, changes: dict[str, bytes | None]) -> None:
    entries = {}
    for rel, after in changes.items():
        path = target / STATE if rel == STATE else _destination(target, rel, module)
        entries[rel] = {"before": _snapshot(path),
                        "after": None if after is None else base64.b64encode(after).decode("ascii")}
    data = _json_bytes({"version": 1, "module": module, "entries": entries})
    if len(data) > MAX_JOURNAL:
        raise ValueError("Transaction exceeds size limit")
    _write_atomic(target / JOURNAL, data)
    try:
        for rel, content in changes.items():
            path = target / STATE if rel == STATE else _destination(target, rel, module)
            if content is None:
                path.unlink(missing_ok=True)
            else:
                _write_atomic(path, content)
        _prune(target, [target / rel for rel in changes if rel != STATE])
    except BaseException:
        _recover(target)
        raise
    (target / JOURNAL).unlink()


def install(module: str, target: Path, *, root: Path = ROOT) -> dict:
    files = _source_files(module, root)
    target = checked_target(target)
    with _lock(target):
        _recover(target)
        state = _state(target)
        previous = state["modules"].get(module, {}).get("files", {})
        planned = {rel: _digest(content) for rel, content in files.items()}
        for rel in set(files) | set(previous):
            path = _destination(target, rel, module)
            if path.exists() and (rel not in previous or not path.is_file() or _digest(path.read_bytes()) != previous[rel]):
                raise FileExistsError(f"Refusing modified or unmanaged file: {path}")
        state["modules"][module] = {"version": VERSION, "files": planned}
        changes = {**files, **{rel: None for rel in previous if rel not in files}, STATE: _json_bytes(state)}
        _transaction(module, target, changes)
    return {"module": module, "version": VERSION, "files": len(planned), "target": str(target)}


def uninstall(module: str, target: Path) -> dict:
    if module not in MODULES:
        raise ValueError(f"Unknown module: {module}")
    target = checked_target(target)
    with _lock(target):
        _recover(target)
        state = _state(target)
        record = state["modules"].get(module)
        if record is None:
            return {"module": module, "removed": 0}
        files = record["files"]
        for rel, digest in files.items():
            path = _destination(target, rel, module)
            if path.exists() and (not path.is_file() or _digest(path.read_bytes()) != digest):
                raise FileExistsError(f"Refusing modified file: {path}")
        del state["modules"][module]
        _transaction(module, target, {**{rel: None for rel in files},
                                     STATE: _json_bytes(state) if state["modules"] else None})
    return {"module": module, "removed": len(files)}


def status(target: Path) -> dict:
    target = checked_target(target)
    state = _state(target)
    integrity = {}
    for module, record in state["modules"].items():
        changed = []
        for rel, digest in record["files"].items():
            path = _destination(target, rel, module)
            if not path.is_file() or _digest(path.read_bytes()) != digest:
                changed.append(rel)
        integrity[module] = {"version": record.get("version", "legacy"), "modified_or_missing": changed}
    return {"installed": sorted(state["modules"]), "integrity": integrity,
            "recovery_required": (target / JOURNAL).exists() or (target / LOCK).exists()}
