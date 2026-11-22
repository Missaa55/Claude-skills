"""Portable metadata/setup helper; no accounts, API keys, model execution or paid calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import sys


def safe(path):
    path = Path(os.path.abspath(Path(path).expanduser()))
    if sys.platform == "darwin":
        for alias in (Path("/var"), Path("/tmp"), Path("/etc")):
            expected = Path("/private") / alias.name
            if path.is_relative_to(alias) and alias.is_symlink() and alias.lstat().st_uid == 0 and alias.resolve() == expected:
                path = expected / path.relative_to(alias)
                break
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            # Only verified root-owned macOS aliases were normalized above.
            raise ValueError("Linked path rejected")
    return path


def write_new(path, value):
    path = safe(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def setup(directory):
    directory = safe(directory)
    path = directory / "hf-images.mcp.example.json"
    write_new(path, {"mcpServers": {"hf-images": {"type": "http", "url": "https://huggingface.co/mcp?login"}}})
    return {"status": "STATIC CHECK", "configuration": str(path), "authenticated": "NOT VERIFIED",
            "notice": "Sample only. User authorizes connection in Claude/HF; no account settings changed"}


def record(file, output, origin, source_url=None, license_url=None, provider=None):
    file, output = safe(file), safe(output)
    if not file.is_file() or not 24 <= file.stat().st_size <= 32_000_000:
        raise ValueError("Missing or oversized image file")
    content = file.read_bytes()
    dimensions = None
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        dimensions = list(struct.unpack(">II", content[16:24]))
        if not all(1 <= value <= 16000 for value in dimensions):
            raise ValueError("Invalid PNG dimensions")
    elif not (content.startswith(b"\xff\xd8\xff") or content[:4] == b"RIFF" and content[8:12] == b"WEBP"):
        raise ValueError("Only PNG, JPEG or WebP files are accepted")
    for value in (source_url, license_url):
        if value and (not value.startswith("https://") or re.search(r"(?i)(token|key|secret|password)=|https://[^/]*@", value)):
            raise ValueError("Record public HTTPS provenance URLs without credentials")
    if origin == "cc0" and (not source_url or not license_url):
        raise ValueError("CC0 provenance requires original asset and license URLs")
    if origin == "generated" and not provider:
        raise ValueError("Name the actual generating provider")
    data = {"schema_version": 1, "file": file.name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
            "dimensions": dimensions, "origin": origin, "provider": provider, "source_url": source_url,
            "license_url": license_url, "evidence_label": "STATIC CHECK", "visual_review": "NOT VERIFIED",
            "notice": "File/hash metadata only. Origin/license claims and photographic realism need independent review"}
    write_new(output, data)
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    cmd = sub.add_parser("setup")
    cmd.add_argument("--directory", type=Path, required=True)
    cmd = sub.add_parser("record")
    cmd.add_argument("--file", type=Path, required=True)
    cmd.add_argument("--output", type=Path, required=True)
    cmd.add_argument("--origin", choices=("generated", "cc0", "owned", "blender"), required=True)
    cmd.add_argument("--source-url")
    cmd.add_argument("--license-url")
    cmd.add_argument("--provider")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            result = {"claude_cli_available": bool(shutil.which("claude")), "blender_available": bool(shutil.which("blender")),
                      "remote_image_tool": "NOT VERIFIED", "requires_local_gpu": False, "paid_api_required": False,
                      "notice": "Discover actual connected image tools inside Claude; free-provider quota and authentication remain prerequisites"}
        elif args.command == "setup":
            result = setup(args.directory)
        else:
            result = record(args.file, args.output, args.origin, args.source_url, args.license_url, args.provider)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
