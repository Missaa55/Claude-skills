"""Build a runnable stdlib distribution, preserving edited output files."""
import ast
import hashlib
import json
from pathlib import Path
import os
import tempfile

ROOT = Path(__file__).resolve().parent


def build():
    files = [ROOT / "server.py", *sorted((ROOT / "static").glob("*")), *sorted((ROOT / "migrations").glob("*.sql"))]
    ast.parse((ROOT / "server.py").read_text(encoding="utf-8"))
    out = ROOT / "dist"
    if out.is_symlink() or (hasattr(out, "is_junction") and out.is_junction()):
        raise ValueError("Linked output rejected")
    out.mkdir(exist_ok=True)
    manifest = out / "build-manifest.json"
    if manifest.is_symlink():
        raise ValueError("Linked manifest rejected")
    previous = json.loads(manifest.read_text()).get("files", {}) if manifest.exists() else {}
    content = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in files}
    for rel in content:
        path = out / rel
        if path.is_symlink() or any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction()) for p in path.parents if p != out and out in p.parents):
            raise ValueError("Linked output rejected")
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != previous.get(rel):
            raise FileExistsError("Refusing unmanaged or modified output")
    for rel, data in content.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(dir=path.parent)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(temp, path)
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in content.items()}
    manifest.write_text(json.dumps({"files": hashes}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "built", "files": hashes}))


if __name__ == "__main__":
    build()
