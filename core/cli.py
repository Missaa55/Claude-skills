"""Run a local provider CLI, or inspect the planned command without executing."""
import argparse
import json
from pathlib import Path
from .runtime import RunRequest, prepare, execute

def main(argv=None):
    parser = argparse.ArgumentParser(prog="claude-skills")
    parser.add_argument("builder", choices=("web", "app", "minecraft"))
    parser.add_argument("--provider", choices=("claude", "codex"), required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--execute", action="store_true", help="Authorize local provider CLI execution")
    args = parser.parse_args(argv)
    request = RunRequest(args.builder, args.prompt, args.workspace, args.provider, args.timeout)
    result = execute(request, approved=True) if args.execute else prepare(request)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
