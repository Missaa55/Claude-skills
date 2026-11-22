"""Explicitly approved local CLI execution. Working directory is NOT a sandbox."""
from dataclasses import dataclass
from pathlib import Path
import json
import os
import shutil
import subprocess
import time
import uuid

BUILDERS = {"web", "app", "minecraft"}

@dataclass(frozen=True)
class RunRequest:
    builder: str
    prompt: str
    workspace: Path
    provider: str
    timeout: int = 300

def prepare(request: RunRequest) -> dict:
    if request.builder not in BUILDERS:
        raise ValueError("Unknown builder")
    if request.provider not in ("claude", "codex"):
        raise ValueError("Unknown provider")
    if not request.prompt.strip() or len(request.prompt) > 20000:
        raise ValueError("Invalid prompt")
    if not 1 <= request.timeout <= 1800:
        raise ValueError("Invalid timeout")
    workspace = request.workspace.expanduser().resolve(strict=True)
    if not workspace.is_dir():
        raise ValueError("Workspace must be a directory")
    executable = shutil.which(request.provider)
    if not executable:
        raise FileNotFoundError(f"Missing CLI: {request.provider}")
    command = ([executable, "-p", request.prompt] if request.provider == "claude"
               else [executable, "exec", "--skip-git-repo-check", request.prompt])
    return {"builder": request.builder, "provider": request.provider,
            "workspace": str(workspace), "command": command, "timeout": request.timeout}

def execute(request: RunRequest, *, approved: bool = False, log_dir: Path | None = None) -> dict:
    if not approved:
        raise PermissionError("Explicit execution approval required")
    plan = prepare(request)
    workspace = Path(plan["workspace"])
    log_dir = (log_dir or workspace / ".claude-skills" / "runs").resolve()
    if not log_dir.is_relative_to(workspace):
        raise ValueError("Log directory must be within workspace")
    log_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    try:
        result = subprocess.run(plan["command"], cwd=workspace, capture_output=True,
                                text=True, timeout=request.timeout, check=False,
                                stdin=subprocess.DEVNULL)
        status = "success" if result.returncode == 0 else "failed"
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        status, code = "timeout", None
        stdout, stderr = exc.stdout or b"", exc.stderr or b""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", "replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", "replace")
    run_id = uuid.uuid4().hex
    record = {"id": run_id, "builder": request.builder, "provider": request.provider,
              "status": status, "exit_code": code, "elapsed_seconds": round(time.time()-started, 3),
              "stdout": stdout[-100000:], "stderr": stderr[-100000:]}
    path = log_dir / f"{run_id}.json"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    return {"id": run_id, "status": status, "exit_code": code, "log_file": str(path)}
