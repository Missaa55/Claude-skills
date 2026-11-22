"""Independent builder commands. Creation is deterministic; run invokes real AI."""
import argparse
import json
from pathlib import Path
from builders.scaffold import create
from core.pipeline import run_pipeline, verify
from core.process import Policy
from core.runtime import doctor
from quality.cleaner import scan


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("create")
    cmd.add_argument("--spec", type=Path, required=True)
    cmd.add_argument("--workspace", type=Path, required=True)
    for action in ("check", "clean", "run"):
        cmd = sub.add_parser(action)
        cmd.add_argument("builder", choices=("minecraft", "web", "app"))
        cmd.add_argument("--workspace", type=Path, required=True)
        if action != "clean":
            cmd.add_argument("--execute", action="store_true")
            cmd.add_argument("--trusted-local", action="store_true", help="Explicitly acknowledge code review and host execution; not a sandbox")
            cmd.add_argument("--image", help="Already installed Docker image pinned by digest")
        if action == "run":
            cmd.add_argument("--task", required=True)
            cmd.add_argument("--provider", choices=("claude", "codex"), required=True)
            cmd.add_argument("--repairs", type=int, default=1)
    cmd = sub.add_parser("doctor")
    cmd.add_argument("provider", choices=("claude", "codex"))
    cmd = sub.add_parser("research")
    cmd.add_argument("--candidates", type=Path, required=True)
    cmd.add_argument("--output", type=Path, required=True)
    cmd.add_argument("--previous", type=Path)
    cmd = sub.add_parser("design")
    cmd.add_argument("--task", required=True)
    cmd.add_argument("--name", required=True)
    cmd.add_argument("--industry", choices=("electrical", "footwear"), required=True)
    cmd.add_argument("--research", type=Path, required=True)
    cmd.add_argument("--workspace", type=Path, required=True)
    cmd.add_argument("--scroll", choices=("auto", "off", "story"), default="auto")
    args = parser.parse_args(argv)
    try:
        bundle = Path(__file__).resolve().parents[1] / "bundle.json"
        available = json.loads(bundle.read_text())["builder"] if bundle.exists() else None
        selected = json.loads(args.spec.read_text(encoding="utf-8")) if args.command == "create" else None
        builder = selected.get("builder") if selected else "web" if args.command in ("research", "design") else getattr(args, "builder", None)
        if available and builder and builder != available:
            raise ValueError("This standalone package contains only " + available)
        if args.command == "create":
            result = create(selected, args.workspace)
        elif args.command == "doctor":
            result = doctor(args.provider)
        elif args.command == "clean":
            result = scan(args.workspace, args.builder)
        elif args.command == "research":
            from builders.research import collect, compare_samples
            report = collect(json.loads(args.candidates.read_text(encoding="utf-8")))
            if args.previous:
                report["longitudinal_trend"] = compare_samples(report, json.loads(args.previous.read_text(encoding="utf-8")))
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, ensure_ascii=False)
            result = {"status": report["status"], "analyzed": report["analyzed"], "attempted": report["attempted"], "output": str(args.output), "evidence_label": "STATIC CHECK"}
        elif args.command == "design":
            from builders.designer import design
            result = design(args.task, args.name, args.industry, json.loads(args.research.read_text(encoding="utf-8")), args.workspace, scroll=args.scroll)
        else:
            policy = Policy("trusted-local" if args.trusted_local else "docker", args.image)
            if not args.execute:
                result = {"status": "dry_run", "builder": args.builder, "isolation": policy.mode,
                          "notice": "No agent or build commands executed"}
            elif args.command == "check":
                result = verify(args.workspace, args.builder, approved=True, policy=policy)
            else:
                result = run_pipeline(args.builder, args.task, args.workspace, args.provider, approved=True, repair_attempts=args.repairs, policy=policy)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.command in ("check", "run") and args.execute and result["status"] not in ("passed", "checks_passed"):
        return 1
    if args.command == "research" and result["status"] != "ready":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
