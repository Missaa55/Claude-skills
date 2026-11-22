"""Offline modular installer for Claude Code skills."""
import argparse
import json
from pathlib import Path
from .installer import MODULES, install, uninstall, status, recover

def main(argv=None):
    parser = argparse.ArgumentParser(prog="claude-skills")
    sub = parser.add_subparsers(dest="command", required=True)
    for action in ("install", "update", "uninstall"):
        cmd = sub.add_parser(action)
        cmd.add_argument("module", choices=sorted(MODULES))
        cmd.add_argument("--target", type=Path)
        cmd.add_argument("--client", choices=("claude", "codex"), default="claude")
    cmd = sub.add_parser("status")
    cmd.add_argument("--target", type=Path)
    cmd.add_argument("--client", choices=("claude", "codex"), default="claude")
    cmd = sub.add_parser("recover")
    cmd.add_argument("--target", type=Path, required=True)
    cmd.add_argument("--abandoned-lock", action="store_true", help="Remove lock only if its owning process no longer exists")
    args = parser.parse_args(argv)
    if args.target is None:
        args.target = Path.home() / (".agents" if args.client == "codex" else ".claude") / "skills"
    try:
        result = (install(args.module, args.target) if args.command in ("install", "update")
                  else uninstall(args.module, args.target) if args.command == "uninstall"
                  else recover(args.target, abandoned_lock=args.abandoned_lock) if args.command == "recover"
                  else status(args.target))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
