# Experimental builder pipeline

The three builders are independent. `core.pipeline.build_prompt` loads skills from **only** the selected builder; it never loads instructions from the other two builders. It does not depend on keyword routing.

From the repository root:

```bash
python3 -m core.pipeline_cli minecraft --task "Create a Fabric mod" --workspace ./my-mod --provider claude
python3 -m core.pipeline_cli web --task "Build a site" --workspace ./my-site --provider codex
```

The default is a dry run. With `--execute`, the pipeline invokes an installed, authenticated CLI and then runs one predeclared check:

| Builder | Check | Required project file |
| --- | --- | --- |
| web | `npm run build` | `package.json` |
| app | `python -m pytest` | `pyproject.toml` or `pytest.ini` |
| minecraft | `./gradlew build` | `gradlew` |

Optional `--repairs 2` allows up to two additional agent invocations after failed checks. It does not retry missing toolchains or failed agent invocations.

```bash
# ONLY in a trusted, disposable project and with explicit permission:
python3 -m core.pipeline_cli web --task "Build a site" --workspace ./my-site --provider claude --repairs 2 --execute
```

**Security warning:** CLI and build commands can execute arbitrary code inside the workspace and are **not sandboxed**. Do not run on untrusted repositories, expose secrets, or grant unrestricted provider permissions. This is an experimental developer tool, not a public-safe autonomous builder. It does not yet provide browser tests, Minecraft in-game tests, database integration tests, reliable cancellation of child processes, or end-to-end evidence of successful generated applications.
