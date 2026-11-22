"""Opt-in, per-builder agent execution with evidence-based verification.

Local CLI execution is NOT sandboxed. Never run on untrusted repositories.
"""
from dataclasses import dataclass
from pathlib import Path
import json
import shutil
import subprocess
from framework.route import route
from core.runtime import RunRequest, execute

SKILLS = {
    "web": "WebBuilder/skills",
    "app": "AppBuilder/skills",
    "minecraft": "Minecraft/skills",
}
CHECKS = {
    "web": (("npm", "run", "build"),),
    "app": (("python", "-m", "pytest"),),
    "minecraft": (("./gradlew", "build"),),
}
MAX_CONTEXT = 60_000

def build_prompt(builder: str, task: str, *, root: Path | None = None) -> str:
    if builder not in SKILLS:
        raise ValueError("Unknown builder")
    if not task.strip():
        raise ValueError("Empty task")
    root = root or Path(__file__).resolve().parents[1]
    base = root / SKILLS[builder]
    chunks = []
    # Explicit builder selection: NEVER load another builder's skills.
    for file in sorted(base.glob("*/SKILL.md")):
        if file.is_symlink():
            raise ValueError("Skill symlink not allowed")
        chunks.append(f"### {file.parent.name}\n{file.read_text(encoding='utf-8')}")
    if not chunks:
        raise ValueError("No builder skills installed")
    context = "\n\n".join(chunks)
    if len(context) > MAX_CONTEXT:
        raise ValueError("Skill context exceeds safe limit")
    return (f"Selected builder: {builder}. Only use this builder's instructions.\n"
            "Work in the current project directory. Do not deploy, delete user data, "
            "access secrets or run destructive commands without explicit approval.\n"
            f"User task:\n{task}\n\nBuilder skills:\n{context}\n")

def verify(workspace: Path, builder: str, *, timeout: int = 120) -> dict:
    """Run only a predeclared build check. No shell, no user-supplied command."""
    if builder not in CHECKS:
        raise ValueError("Unknown builder")
    workspace = workspace.resolve(strict=True)
    if not workspace.is_dir():
        raise ValueError("Workspace is not a directory")
    command = list(CHECKS[builder][0])
    if builder == "web" and not (workspace / "package.json").is_file():
        return {"status": "not_configured", "reason": "Missing package.json"}
    if builder == "app" and not ((workspace / "pyproject.toml").is_file() or
                                 (workspace / "pytest.ini").is_file()):
        return {"status": "not_configured", "reason": "Missing Python test configuration"}
    if builder == "minecraft":
        if (workspace / "gradlew").is_file():
            command = ["./gradlew", "build"]
        elif shutil.which("gradle"):
            command = ["gradle", "build"]
        else:
            return {"status": "not_configured", "reason": "Missing Gradle wrapper and Gradle executable"}
    try:
        result = subprocess.run(command, cwd=workspace, shell=False,
                                capture_output=True, text=True, timeout=timeout,
                                stdin=subprocess.DEVNULL)
        return {"status": "passed" if result.returncode == 0 else "failed",
                "command": command, "exit_code": result.returncode,
                "stdout": result.stdout[-12000:], "stderr": result.stderr[-12000:]}
    except FileNotFoundError as exc:
        return {"status": "not_configured", "reason": str(exc)}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "command": command}

def run_pipeline(builder: str, task: str, workspace: Path, provider: str,
                 *, approved: bool = False, repair_attempts: int = 0) -> dict:
    if not approved:
        raise PermissionError("Explicit permission required for agent and build commands")
    if repair_attempts not in range(0, 4):
        raise ValueError("repair_attempts must be between 0 and 3")
    prompt = build_prompt(builder, task)
    events = []
    for attempt in range(repair_attempts + 1):
        agent = execute(RunRequest(builder, prompt, workspace, provider), approved=True)
        events.append({"attempt": attempt + 1, "agent": agent})
        if agent["status"] != "success":
            break
        check = verify(workspace, builder)
        events[-1]["verification"] = check
        if check["status"] == "passed":
            break
        if check["status"] != "failed" or attempt == repair_attempts:
            break
        # The failed check's output is evidence for a bounded repair request.
        prompt = build_prompt(builder, task) + (
            "\nPrevious build failed. Fix only the relevant errors and rerun checks.\n"
            + json.dumps(check, ensure_ascii=False)[-14000:])
    final = events[-1]
    verified = final.get("verification", {}).get("status") == "passed"
    return {"builder": builder, "task": task, "events": events,
            "verified": verified, "status": "verified" if verified else "unverified"}
