"""Offline modular installer for Claude Code skills."""
import argparse
import json
from pathlib import Path
from .installer import MODULES, install, uninstall, status

def main(argv=None):
    parser = argparse.ArgumentParser(prog="claude-skills")
    sub = parser.add_subparsers(dest="command", required=True)
    for action in ("install", "uninstall"):
        cmd = sub.add_parser(action)
        cmd.add_argument("module", choices=sorted(MODULES))
        cmd.add_argument("--target", type=Path, default=Path.home() / ".claude" / "skills")
    cmd = sub.add_parser("status")
    cmd.add_argument("--target", type=Path, default=Path.home() / ".claude" / "skills")
    args = parser.parse_args(argv)
    try:
        result = (install(args.module, args.target) if args.command == "install"
                  else uninstall(args.module, args.target) if args.command == "uninstall"
                  else status(args.target))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
