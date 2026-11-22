"""Dependency-free static production build. Never recursively deletes output."""
from pathlib import Path
import hashlib
import json
import os
import tempfile

ROOT = Path(__file__).resolve().parent
FILES = ("index.html", "style.css", "site.js", "mark.svg")


def build():
    out = ROOT / "dist"
    if out.is_symlink() or (hasattr(out, "is_junction") and out.is_junction()):
        raise ValueError("Linked output rejected")
    out.mkdir(exist_ok=True)
    metadata = out / "build-manifest.json"
    if metadata.is_symlink():
        raise ValueError("Linked manifest rejected")
    previous = json.loads(metadata.read_text()).get("files", {}) if metadata.exists() else {}
    data = {name: (ROOT / name).read_bytes() for name in FILES}
    assert b"@@NAME@@" not in data["index.html"], "Generate the template before building"
    for name in FILES:
        path = out / name
        if path.is_symlink() or (path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() != previous.get(name)):
            raise FileExistsError(f"Refusing unmanaged or changed build output: {name}")
    for name, content in data.items():
        fd, temp = tempfile.mkstemp(dir=out)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        os.replace(temp, out / name)
    hashes = {name: hashlib.sha256(content).hexdigest() for name, content in data.items()}
    metadata.write_text(json.dumps({"files": hashes}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "built", "files": hashes}))


if __name__ == "__main__":
    build()
