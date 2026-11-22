"""Bounded orchestration. Verification scope is explicit; agent exit is not evidence."""
from pathlib import Path
import json
import re
import shutil
import sys
import uuid
import zipfile
from core.artifacts import inspect
from core.process import Policy, run, redact
from core.runtime import RunRequest, execute
from distribution.installer import checked_target, _write_atomic
from quality.cleaner import scan

SKILLS = {"web": "WebBuilder/skills", "app": "AppBuilder/skills", "minecraft": "Minecraft/skills"}
MAX_CONTEXT = 60_000


def select_builder(task: str) -> str:
    patterns = {"minecraft": r"minecraft|fabric|neoforge|paper plugin|datapack",
                "web": r"website|webbuilder|landing page|webov|web str|responzivní web",
                "app": r"appbuilder|aplikac|build an app|backend|rest api"}
    hits = [key for key, pattern in patterns.items() if re.search(pattern, task, re.I)]
    if len(hits) != 1:
        raise ValueError("Ambiguous builder; choose web, app or minecraft explicitly")
    return hits[0]


def build_prompt(builder: str, task: str, *, root: Path | None = None) -> str:
    if builder not in SKILLS or not isinstance(task, str) or not 1 <= len(task.strip()) <= 6000:
        raise ValueError("Invalid builder or task")
    root = root or Path(__file__).resolve().parents[1]
    base = checked_target(root / SKILLS[builder])
    chunks = []
    selected = None
    if builder == "minecraft":
        selected = {"minecraft-architecture", "minecraft-testing", "minecraft-assets", "minecraft-release", "minecraft-quality-cleaner"}
        for target in ("fabric", "neoforge", "paper", "datapack", "worldgen"):
            if re.search(r"\b" + target + r"\b", task, re.I):
                selected.add("minecraft-" + target)
    elif builder == "web":
        selected = {"webbuilder-orchestrator", "webbuilder-design-system", "webbuilder-layout", "webbuilder-content-seo", "webbuilder-accessibility", "webbuilder-performance", "webbuilder-visual-qa", "webbuilder-security", "webbuilder-quality-cleaner", "webbuilder-research"}
        if re.search(r"\bcms\b", task, re.I):
            selected.add("webbuilder-cms")
        if re.search(r"image|photo|obráz|obraz|fot|blender|cc0|asset", task, re.I):
            selected.add("claude-image-studio")
    for file in sorted(base.glob("*/SKILL.md")):
        if selected is not None and file.parent.name not in selected:
            continue
        checked_target(file)
        if file.stat().st_size > 20000:
            raise ValueError("Oversized skill")
        chunks.append(f"### {file.parent.name}\n{file.read_text(encoding='utf-8')}")
    context = "\n\n".join(chunks)
    if not chunks or len(context) > MAX_CONTEXT:
        raise ValueError("Missing or oversized builder context")
    return (f"Selected builder: {builder}. Use only its skill context.\n"
            "Work only in the current disposable workspace. Never deploy, access credentials, "
            "delete user data or invoke destructive commands. Stop when approval is needed.\n"
            "Implement a runnable project with reproducible tests and actual production outputs. "
            "Do not claim browser or game verification unless executed.\n"
            f"User task:\n{task}\n\nBuilder skills:\n{context}\n")


def verify(workspace: Path, builder: str, *, timeout: int = 120, approved: bool = False,
           policy: Policy | None = None, cancel=None) -> dict:
    if builder not in SKILLS:
        raise ValueError("Unknown builder")
    workspace = checked_target(workspace)
    policy = policy or Policy()
    commands = []
    python = sys.executable if policy.mode == "trusted-local" else "python3"
    if builder in ("web", "app"):
        if not (workspace / "build.py").is_file() or not (workspace / "tests").is_dir():
            return {"status": "not_configured", "reason": "Require reviewed build.py and tests/; no arbitrary command inference"}
        # Refuse an empty test suite, even if unittest would exit zero.
        if not any((workspace / "tests").glob("test_*.py")):
            return {"status": "not_configured", "reason": "No tests found"}
        commands = [[python, "build.py"], [python, "-m", "unittest", "discover", "-s", "tests", "-v"]]
    else:
        if not (workspace / "build.gradle").is_file():
            return {"status": "not_configured", "reason": "Missing build.gradle"}
        if policy.mode == "trusted-local" and sys.platform == "win32":
            gradle = shutil.which("gradle")
            # Batch files never receive generated shell text. Require a native Gradle
            # launcher or use the CI Linux/container workflow for Java projects.
            if not gradle or gradle.endswith((".bat", ".cmd")):
                return {"status": "not_configured", "reason": "Use Linux/container Gradle or a native executable"}
        else:
            gradle = "./gradlew" if (workspace / "gradlew").is_file() else "gradle"
        commands = [[gradle, "--no-daemon", "build"]]
    results = []
    for command in commands:
        try:
            result = run(command, workspace, approved=approved, policy=policy, timeout=timeout, cancel=cancel)
        except (OSError, ValueError) as exc:
            return {"status": "not_configured", "reason": redact(str(exc)), "checks": results}
        results.append({"command": command, **result})
        if result["status"] != "passed":
            return {"status": result["status"], "checks": results}
        if "unittest" in command and not re.search(r"Ran [1-9][0-9]* tests? in", result["stderr"] + result["stdout"]):
            return {"status": "failed", "reason": "No executed tests in runner output", "checks": results}
    try:
        artifacts = inspect(workspace, builder)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        return {"status": "failed", "reason": str(exc), "checks": results, "artifacts": []}
    cleaner = scan(workspace, builder)
    return {"status": "passed", "checks": results, "artifacts": artifacts,
            "quality": cleaner, "evidence_label": "REAL VERIFIED",
            "scope": "Build, declared tests and independent output inspection only; browser/game/production readiness are separate gates"}


def run_pipeline(builder: str, task: str, workspace: Path, provider: str, *, approved: bool = False,
                 repair_attempts: int = 0, policy: Policy | None = None, cancel=None) -> dict:
    if not approved:
        raise PermissionError("Explicit execution approval required")
    if type(repair_attempts) is not int or not 0 <= repair_attempts <= 3:
        raise ValueError("repair_attempts must be between 0 and 3")
    builder = select_builder(task) if builder == "auto" else builder
    prompt = build_prompt(builder, task)
    workspace = checked_target(workspace)
    if not workspace.is_dir():
        raise FileNotFoundError(workspace)
    events = []
    identity = uuid.uuid4().hex
    log_dir = checked_target(workspace / ".claude-skills/pipelines")
    report = {"id": identity, "builder": builder, "events": events, "verified": False,
              "status": "planned", "evidence_label": "NOT VERIFIED", "repair_limit": repair_attempts}
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / (identity + ".json")
    def save():
        _write_atomic(path, (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode())
    save()
    try:
        for attempt in range(repair_attempts + 1):
            if cancel is not None and cancel.is_set():
                report["status"] = "cancelled"
                break
            report["status"] = "generating" if attempt == 0 else "repairing"
            save()
            agent = execute(RunRequest(builder, prompt, workspace, provider, policy=policy or Policy()), approved=True, cancel=cancel)
            events.append({"attempt": attempt + 1, "agent": agent})
            save()
            if agent["status"] != "success":
                report["status"] = agent["status"]
                break
            report["status"] = "testing"
            save()
            check = verify(workspace, builder, approved=True, policy=policy, cancel=cancel)
            events[-1]["verification"] = check
            if check["status"] == "passed" and check.get("artifacts"):
                report.update(verified=True, status="checks_passed", evidence_label="REAL VERIFIED", scope=check.get("scope"))
                break
            report["status"] = check["status"]
            if check["status"] != "failed" or attempt == repair_attempts:
                break
            prompt = build_prompt(builder, task) + "\nRepair only the evidenced failures:\n" + json.dumps(check, ensure_ascii=False)[-14000:]
    except (OSError, ValueError) as exc:
        report.update(status="blocked", reason=redact(str(exc)))
    except KeyboardInterrupt:
        report["status"] = "cancelled"
    finally:
        save()
    return {**report, "log_file": str(path)}
