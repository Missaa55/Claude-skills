"""Independent, bounded artifact inspection; never imports generated code."""
import hashlib
import json
from pathlib import Path
import zipfile
from distribution.installer import checked_target


def inspect(workspace: Path, builder: str) -> list[dict]:
    root = checked_target(workspace)
    selected = []
    if builder == "web":
        required = ("dist/index.html", "dist/style.css", "dist/site.js")
    elif builder == "app":
        required = ("dist/server.py", "dist/static/index.html", "dist/static/app.js", "dist/migrations/001_initial.sql")
    elif builder == "minecraft":
        required = tuple(p.relative_to(root).as_posix() for p in (root / "build/libs").glob("*.jar")
                         if not p.name.endswith(("-sources.jar", "-dev.jar")))
        if not required:
            raise ValueError("No production JAR found")
    else:
        raise ValueError("Unknown builder")
    for rel in required:
        path = checked_target(root / rel)
        if not path.is_file() or not 0 < path.stat().st_size <= 64_000_000:
            raise ValueError(f"Missing, empty or oversized output: {rel}")
        data = path.read_bytes()
        if rel.endswith(".html") and (b"<html" not in data.lower() or b"<title>" not in data.lower() or b"@@NAME@@" in data):
            raise ValueError("Invalid or unexpanded HTML output")
        if builder == "minecraft":
            with zipfile.ZipFile(path) as jar:
                names = jar.namelist()
                if len(names) > 10000 or sum(info.file_size for info in jar.infolist()) > 128_000_000:
                    raise ValueError("Oversized JAR")
                if not any(n.endswith(".class") for n in names):
                    raise ValueError("JAR contains no compiled classes")
                if not any(n in names for n in ("fabric.mod.json", "plugin.yml", "META-INF/neoforge.mods.toml")):
                    raise ValueError("JAR contains no loader metadata")
                if "fabric.mod.json" in names:
                    meta = json.loads(jar.read("fabric.mod.json"))
                    if not meta.get("id") or not meta.get("entrypoints", {}).get("main"):
                        raise ValueError("Fabric metadata lacks entrypoint")
                    for entry in meta["entrypoints"]["main"]:
                        if not isinstance(entry, str) or entry.replace(".", "/") + ".class" not in names:
                            raise ValueError("Fabric entrypoint class absent")
        selected.append({"path": rel, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return selected
