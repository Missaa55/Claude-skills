"""CLI for opt-in builder pipeline. No commands run without --execute."""
import argparse
import json
from pathlib import Path
from core.pipeline import build_prompt, run_pipeline

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("builder", choices=("web", "app", "minecraft"))
    parser.add_argument("--task", required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--provider", choices=("claude", "codex"), required=True)
    parser.add_argument("--repairs", type=int, default=0)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute:
        result = {"status": "dry_run", "builder": args.builder,
                  "workspace": str(args.workspace),
                  "context_characters": len(build_prompt(args.builder, args.task)),
                  "notice": "No agent or build commands were executed"}
    else:
        result = run_pipeline(args.builder, args.task, args.workspace,
                              args.provider, approved=True, repair_attempts=args.repairs)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
