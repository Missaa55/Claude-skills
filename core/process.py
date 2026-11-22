"""Bounded process execution. Host mode is only for explicitly reviewed code."""
from dataclasses import dataclass
from pathlib import Path
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import uuid
from distribution.installer import checked_target

MAX_OUTPUT = 2_000_000
ENV_KEYS = {"PATH", "SystemRoot", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT",
            "LANG", "LC_ALL", "JAVA_HOME"}


def redact(value: str) -> str:
    for key, secret in os.environ.items():
        if len(secret) >= 8 and re.search(r"(?i)(token|secret|password|api.?key|credential)", key):
            value = value.replace(secret, "[REDACTED]")
    value = re.sub(r"(?i)\b(?:sk-[\w-]{12,}|ghp_[\w]{12,}|github_pat_[\w_]{12,})\b", "[REDACTED]", value)
    value = re.sub(r"(?i)(bearer\s+)[^\s\"']+", r"\1[REDACTED]", value)
    return re.sub(r'(?i)(\b(?:[\w-]*[_-])?(?:password|secret|token|api[_-]?key)\b[\"\']?\s*[:=]\s*)[^\s,}\n]+',
                  r'\1[REDACTED]', value)


@dataclass(frozen=True)
class Policy:
    mode: str = "docker"
    image: str | None = None
    network: bool = False
    approved_network: bool = False


def isolated_command(command: list[str], workspace: Path, policy: Policy) -> list[str]:
    if policy.mode == "trusted-local":
        return command
    if policy.mode != "docker":
        raise ValueError("Unknown execution policy")
    docker = shutil.which("docker")
    if not docker:
        raise FileNotFoundError("Docker is required for untrusted execution; no host fallback")
    if not policy.image or not re.fullmatch(r"(?:[a-zA-Z0-9./:_-]+@)?sha256:[0-9a-f]{64}", policy.image):
        raise ValueError("Use an already installed image pinned by sha256 digest")
    if policy.network and not policy.approved_network:
        raise PermissionError("Container network requires separate explicit approval")
    if any(c in str(workspace) for c in (",", "\n", "\r")):
        raise ValueError("Unsupported mount path")
    return [docker, "run", "--rm", "--init", "--name=builder-" + uuid.uuid4().hex, "--pull=never", "--read-only", "--cap-drop=ALL",
            "--security-opt=no-new-privileges", "--pids-limit=128", "--memory=2g", "--cpus=2",
            "--network=bridge" if policy.network else "--network=none", "--user=65532:65532",
            "--tmpfs=/tmp:rw,noexec,nosuid,size=256m", "--env=HOME=/tmp",
            "--mount", f"type=bind,source={workspace},target=/workspace", "--workdir=/workspace",
            policy.image, *command]


class _WindowsJob:
    """Assign a suspended process before resuming: descendants inherit kill-on-close."""
    def __init__(self, process):
        import ctypes as c
        from ctypes import wintypes as w
        self.c = c
        self.k = c.WinDLL("kernel32", use_last_error=True)
        k = self.k
        k.CreateJobObjectW.restype = w.HANDLE
        k.OpenThread.restype = w.HANDLE
        k.CreateToolhelp32Snapshot.restype = w.HANDLE
        k.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
        k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        k.CloseHandle.argtypes = [w.HANDLE]
        k.ResumeThread.argtypes = [w.HANDLE]
        class Basic(c.Structure):
            _fields_ = [("per_process", c.c_int64), ("per_job", c.c_int64), ("flags", w.DWORD),
                        ("min", c.c_size_t), ("max", c.c_size_t), ("active", w.DWORD),
                        ("affinity", c.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]
        class IO(c.Structure):
            _fields_ = [(name, c.c_uint64) for name in ("ro", "wo", "oo", "rt", "wt", "ot")]
        class Extended(c.Structure):
            _fields_ = [("basic", Basic), ("io", IO), ("process_memory", c.c_size_t),
                        ("job_memory", c.c_size_t), ("peak_process", c.c_size_t), ("peak_job", c.c_size_t)]
        class ThreadEntry(c.Structure):
            _fields_ = [("size", w.DWORD), ("usage", w.DWORD), ("id", w.DWORD),
                        ("pid", w.DWORD), ("priority", c.c_long), ("delta", c.c_long), ("flags", w.DWORD)]
        k.Thread32First.argtypes = [w.HANDLE, c.POINTER(ThreadEntry)]
        k.Thread32Next.argtypes = [w.HANDLE, c.POINTER(ThreadEntry)]
        self.handle = k.CreateJobObjectW(None, None)
        if not self.handle:
            raise OSError(c.get_last_error(), "Cannot create process job")
        try:
            limits = Extended()
            limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not k.SetInformationJobObject(self.handle, 9, c.byref(limits), c.sizeof(limits)):
                raise OSError(c.get_last_error(), "Cannot configure process job")
            if not k.AssignProcessToJobObject(self.handle, int(process._handle)):
                raise OSError(c.get_last_error(), "Cannot contain process; execution refused")
            snap = k.CreateToolhelp32Snapshot(4, 0)
            if snap == c.c_void_p(-1).value:
                raise OSError(c.get_last_error(), "Cannot inspect suspended process")
            resumed = False
            try:
                entry = ThreadEntry()
                entry.size = c.sizeof(entry)
                more = k.Thread32First(snap, c.byref(entry))
                while more:
                    if entry.pid == process.pid:
                        thread = k.OpenThread(2, False, entry.id)
                        if thread:
                            resumed = k.ResumeThread(thread) != 0xffffffff
                            k.CloseHandle(thread)
                        break
                    more = k.Thread32Next(snap, c.byref(entry))
            finally:
                k.CloseHandle(snap)
            if not resumed:
                raise OSError("Cannot resume contained process")
        except BaseException:
            self.close()
            process.kill()
            process.wait()
            raise

    def close(self):
        if self.handle:
            self.k.CloseHandle(self.handle)
            self.handle = None


def run(command: list[str], workspace: Path, *, approved: bool = False,
        policy: Policy | None = None, timeout: float = 120, cancel: threading.Event | None = None,
        stdin: str | None = None, max_output: int = MAX_OUTPUT) -> dict:
    if not approved:
        raise PermissionError("Execution approval required")
    if not 0 < timeout <= 1800 or not 1024 <= max_output <= 10_000_000:
        raise ValueError("Invalid process limits")
    if not command or any(not isinstance(p, str) or "\x00" in p for p in command):
        raise ValueError("Invalid argument vector")
    workspace = checked_target(workspace)
    if not workspace.is_dir():
        raise FileNotFoundError(workspace)
    command = isolated_command(command, workspace, policy or Policy())
    env = {key: value for key, value in os.environ.items() if key in ENV_KEYS}
    chunks = {"stdout": bytearray(), "stderr": bytearray()}
    overflow = threading.Event()
    started = time.monotonic()
    job = None
    with tempfile.TemporaryDirectory(prefix="builder-process-") as home:
        env.update({"HOME": home, "USERPROFILE": home, "TEMP": home, "TMP": home,
                    "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "CI": "1"})
        process = subprocess.Popen(command, cwd=workspace, env=env, shell=False,
                                   stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=os.name != "nt",
                                   creationflags=0x4 | 0x08000000 if os.name == "nt" else 0)
        try:
            if os.name == "nt":
                job = _WindowsJob(process)
            def reader(stream, key):
                while block := stream.read(4096):
                    room = max_output - len(chunks[key])
                    chunks[key].extend(block[:max(room, 0)])
                    if len(block) > room:
                        overflow.set()
            readers = [threading.Thread(target=reader, args=(getattr(process, key), key), daemon=True)
                       for key in chunks]
            for thread in readers:
                thread.start()
            def writer():
                try:
                    process.stdin.write(stdin.encode("utf-8"))
                    process.stdin.close()
                except (OSError, ValueError):
                    pass
            if stdin is not None:
                threading.Thread(target=writer, daemon=True).start()
            status = None
            while process.poll() is None:
                if cancel is not None and cancel.is_set():
                    status = "cancelled"
                elif overflow.is_set():
                    status = "output_limit"
                elif time.monotonic() - started >= timeout:
                    status = "timeout"
                if status:
                    break
                time.sleep(0.025)
        except KeyboardInterrupt:
            status = "cancelled"
        finally:
            if job:
                job.close()
            elif os.name != "nt":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif process.poll() is None:
                process.kill()
            process.wait(timeout=10)
            if (policy or Policy()).mode == "docker":
                container = next(p.split("=", 1)[1] for p in command if p.startswith("--name=builder-"))
                cleanup = subprocess.run([command[0], "rm", "--force", container], env=env, stdin=subprocess.DEVNULL,
                                         capture_output=True, timeout=15, shell=False)
                if cleanup.returncode and b"No such container" not in cleanup.stderr:
                    status = "cleanup_failed"
            for thread in locals().get("readers", []):
                thread.join(timeout=5)
            for stream in (process.stdout, process.stderr, process.stdin):
                if stream:
                    stream.close()
    return {"status": status or ("output_limit" if overflow.is_set() else "passed" if process.returncode == 0 else "failed"),
            "exit_code": process.returncode, "elapsed_seconds": round(time.monotonic() - started, 3),
            **{key: redact(value.decode("utf-8", "replace")) for key, value in chunks.items()}}
