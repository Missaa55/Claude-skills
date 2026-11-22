"""Provider adapters. Isolation is required unless reviewed host execution is explicit."""
from dataclasses import dataclass
from pathlib import Path
import json
import os
import shutil
import uuid
from core.process import Policy, run, redact
from distribution.installer import checked_target

BUILDERS = {"web", "app", "minecraft"}


@dataclass(frozen=True)
class RunRequest:
    builder: str
    prompt: str
    workspace: Path
    provider: str
    timeout: int = 300
    policy: Policy = Policy()


def prepare(request: RunRequest) -> dict:
    if request.builder not in BUILDERS or request.provider not in ("claude", "codex"):
        raise ValueError("Unknown builder or provider")
    if not isinstance(request.prompt, str) or not request.prompt.strip() or len(request.prompt) > 100_000:
        raise ValueError("Invalid prompt")
    if not 1 <= request.timeout <= 1800:
        raise ValueError("Invalid timeout")
    workspace = checked_target(request.workspace)
    if not workspace.is_dir():
        raise FileNotFoundError("Workspace must exist")
    executable = shutil.which(request.provider) if request.policy.mode == "trusted-local" else request.provider
    if not executable:
        raise FileNotFoundError(f"Missing CLI: {request.provider}")
    if str(executable).endswith((".cmd", ".bat")):
        raise ValueError("Use a native provider executable; shell launchers are not allowed")
    # Prompts travel over stdin, never through a shell or the process command line.
    command = ([executable, "-p", "--output-format", "json", "--max-turns", "12"]
               if request.provider == "claude" else
               [executable, "exec", "--skip-git-repo-check", "--ephemeral", "--ignore-user-config",
                "--ignore-rules", "--sandbox", "workspace-write", "--json", "-"])
    return {"builder": request.builder, "provider": request.provider, "workspace": str(workspace),
            "command": command, "timeout": request.timeout, "isolation": request.policy.mode}


def doctor(provider: str) -> dict:
    if provider not in ("claude", "codex"):
        raise ValueError("Unknown provider")
    executable = shutil.which(provider)
    return {"provider": provider, "available_on_host": bool(executable),
            "executable": executable, "authenticated": "NOT VERIFIED",
            "docker_available": bool(shutil.which("docker")),
            "notice": "Executable presence does not prove authentication or container readiness"}


def _usage(stdout: str) -> dict:
    usage = {}
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            data = event.get("usage")
            if not isinstance(data, dict) and isinstance(event.get("result"), dict):
                data = event["result"].get("usage")
            if isinstance(data, dict):
                for key in ("input_tokens", "output_tokens", "cached_input_tokens"):
                    if type(data.get(key)) is int and data[key] >= 0:
                        usage[key] = data[key]
            cost = event.get("total_cost_usd")
            if type(cost) in (int, float) and 0 <= cost < 100000:
                usage["reported_cost_usd"] = cost
    return {"tokens": usage or None, "estimated_cost_usd": None}


def execute(request: RunRequest, *, approved: bool = False, log_dir: Path | None = None, cancel=None) -> dict:
    if not approved:
        raise PermissionError("Explicit execution approval required")
    plan = prepare(request)
    workspace = Path(plan["workspace"])
    log_dir = checked_target(log_dir or workspace / ".claude-skills/runs")
    if not log_dir.is_relative_to(workspace):
        raise ValueError("Log directory must be within workspace")
    log_dir.mkdir(parents=True, exist_ok=True)
    result = run(plan["command"], workspace, approved=True, policy=request.policy,
                 timeout=request.timeout, cancel=cancel, stdin=request.prompt)
    run_id = uuid.uuid4().hex
    status = "success" if result["status"] == "passed" else result["status"]
    record = {"id": run_id, "builder": request.builder, "provider": request.provider,
              **result, "status": status, "verification": "NOT VERIFIED", **_usage(result["stdout"])}
    path = log_dir / f"{run_id}.json"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    return {"id": run_id, "status": status, "exit_code": result["exit_code"],
            "log_file": str(path), **_usage(result["stdout"])}
