# Independent installation and ZIP distributions

Python 3.11+ is required. Each builder can be installed alone or in any of seven combinations.
The installer includes skills, the standalone Cleaner and a complete selected runtime under:

| Module | Runtime launcher inside the skills target |
| --- | --- |
| minecraft | `minecraft-architecture/runtime/builder.py` |
| app | `appbuilder-orchestrator/runtime/builder.py` |
| web | `webbuilder-orchestrator/runtime/builder.py` |

```bash
python -m distribution.cli install web --target ../review-skills
python -m distribution.cli status --target ../review-skills
python -m distribution.cli update web --target ../review-skills
python -m distribution.cli uninstall web --target ../review-skills
```

`--target` is recommended for an initial disposable review. Without it the default is
`~/.claude/skills`; `--client codex` selects `~/.agents/skills`, as documented in the
[official Codex skill guide](https://learn.chatgpt.com/docs/build-skills).
Skill format compatibility is statically checked; authenticated client discovery/execution
is not established by installing files.

The runtime runs from any working directory. For example, with the web installation above:

```bash
python ../review-skills/webbuilder-orchestrator/runtime/builder.py create --spec ../review-skills/webbuilder-orchestrator/runtime/examples/briefs/web.json --workspace ../new-site
```

Updates use the same installed version's command and refuse any modified or unmanaged
destination, even one whose bytes happen to match. Status lists missing/changed hashes.
Uninstall removes only recorded, unchanged module files and prunes empty owned directories.
Unknown user files remain. A directory lock rejects concurrent operations without waiting.

Writes/removal are journalled. On an ordinary exception the transaction rolls back; an
interrupted transaction is recovered before the next operation. If a crash leaves a lock,
inspect its owner and explicitly use:

```bash
python -m distribution.cli recover --target ../review-skills --abandoned-lock
```

Recovery refuses a live lock owner, invalid journal or subsequent user edits. Never manually
delete user files to resolve an update conflict. Copy your changes to a separate backup,
review the expected original hashes and restore/migrate deliberately.

Build standalone archives with:

```bash
python -m distribution.bundle build all --output ../packages
```

Each `claude-skills-MODULE-0.2.0.zip` contains one builder, `builder.py`, an example brief,
installation commands and `CHECKSUMS.json`. Extract into a **new directory**, compare the
archive's `.sha256` against the trusted CI artifact, then run
`python -m distribution.bundle verify .` before use. No other builder/repository checkout
is needed. Normal use may add project files outside the package; verification deliberately
rejects unexpected files inside the extracted package. Check archives before running them.

Hashes provide corruption/integrity checks, not cryptographic publisher identity. No signed
installer or automatic self-updater is claimed. Toolchains and provider credentials are
separate. CI tests lifecycle/update/bundles on Windows, Linux and macOS; see the current
[verification report](../docs/VERIFICATION.md), not the historical file-count tables.

`claude-image-studio-0.2.0.zip` is an additional, standalone Claude skill upload, not a
fourth development Builder. Its ZIP contains the skill folder at the root. Upload it
through Claude's Skills interface or extract into a new Claude Code skills folder;
see the [Czech connection guide](../docs/USER_GUIDE.cs.md). No image model, paid API key
or Blender executable is embedded. Image-provider authentication is separate.
