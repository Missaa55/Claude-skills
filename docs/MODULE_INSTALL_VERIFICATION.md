# Independent builder installation: verified lifecycle

Tested 2026-11-22 using a disposable GitHub Actions checkout and temporary directories.

- [Completed successful 9-job matrix run](https://github.com/Missaa55/Claude-skills/actions/runs/45053267859)
- [Completed successful validation suite](https://github.com/Missaa55/Claude-skills/actions/runs/45053267855)
- Script: `python scripts/smoke_modules.py all`
- Jobs: Minecraft / AppBuilder / WebBuilder, each on Ubuntu, Windows and macOS (nine independently executed jobs).

## What each job actually does

1. Invoke the real `python -m distribution.cli install <builder> --target <temporary-directory>` command in a child process.
2. Confirm the installed skills exactly equal the selected builder's source skill names; there is no other builder's installation.
3. Run the actual `scripts/cleaner.py` bundled inside that installed builder, on a small synthetic project with deliberate placeholder text and a backup file.
4. Confirm the cleaner identified both sample issues without mutating any project files or protected files.
5. Execute `core.pipeline_cli` in dry-run mode, which checks builder skill context but does not call an external AI.
6. Install the same module again to check idempotence.
7. Uninstall the module and confirm **zero files or directories** remain in the temporary skills target, including the installer state file.
8. Let the temporary directory be deleted when the smoke-test subprocess exits.

## Actual results

| Runner | Minecraft | AppBuilder | WebBuilder |
| --- | --- | --- | --- |
| Ubuntu | PASS | PASS | PASS |
| Windows | PASS | PASS | PASS |
| macOS | PASS | PASS | PASS |

On Ubuntu, Minecraft installed 12 skills and a cleaner script (13 files), found two synthetic issues, removed all 13 installed files, and left no files behind.

## What this does not prove

- No real Claude Code or Codex agent was invoked; no account or API credentials were used.
- No new application or website was autonomously generated or deployed.
- This matrix does not test running Minecraft itself. A separate real Fabric 1.21.1 build is documented in [the Fabric example](../examples/fabric-1211/README.md).
- The cleaner is heuristic; no definitive AI-origin detection or arbitrary safe deletion is claimed.
- End users still need the repository checkout and Python to run this version of the installer; independently downloadable packages are a future distribution task.
- Temporary directories in CI were cleaned up; this process did not install or delete anything on a user's personal computer.
