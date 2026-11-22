# Execution and verification

Dry-run is the default:

```bash
python -m core.pipeline_cli web --task "Create a website" --workspace ./empty-project --provider codex
python -m core.builder_cli doctor codex
```

`doctor` reports executable/container availability, never infers authentication. The
provider adapters send prompts over stdin, request structured completion and reject invalid
or partial responses even when exit status is zero. Usage/cost fields are recorded only
when reported by the provider; missing cost remains null.

To request untrusted execution:

```bash
python -m core.pipeline_cli web --task "Create a website" --workspace ./disposable-project --provider codex --repairs 2 --execute --image registry/image@sha256:YOUR_VERIFIED_DIGEST
```

The illustrative digest must be replaced with a real installed image. Docker is mandatory,
network is disabled, no host credentials/home/socket are mounted, and no host fallback exists.
Authenticated Claude/Codex container setup is **NOT VERIFIED** and no credential broker is
implemented. The offline CLI policy cannot reach a remote provider; preparing an image
alone does not solve that. Provider authentication and controlled egress still require
implementation/review before a real AI run can work. Expect a blocked/failed result.
Do not use host execution to work around this boundary for untrusted AI output.

For the repository-owned, reviewed reference templates only:

```bash
python -m core.builder_cli check web --workspace ./generated-site --execute --trusted-local
python -m core.builder_cli check app --workspace ./generated-app --execute --trusted-local
```

Web/app checks require `build.py`, a nonempty `tests/test_*.py` suite and actual reported
test execution. They run the build and HTTP/database tests, inspect nonempty production
outputs and hash them. Minecraft checks require Gradle configuration and a compiled JAR
with loader metadata and actual entrypoint classes. Native Windows batch launchers are
not accepted by the runtime; use the Linux CI Minecraft workflow.

The `checks_passed` result means precisely the recorded build/tests/artifact scope.
It does not establish visual quality, full accessibility, in-game client behavior or
production security. Run the dedicated evidence scripts for those independent gates:

```bash
python scripts/qa_browser.py --output .artifacts/browser-new
python scripts/qa_minecraft.py --kind fabric --output .artifacts/fabric-new
python scripts/qa_designer.py --workspace ../two-designs --output .artifacts/design-new
```

`qa_minecraft.py --accept-eula` additionally starts a new loopback-only synthetic Fabric
world, asserts block/item/recipe registration and stops cleanly. That flag is explicit
acceptance of the [Minecraft EULA](https://www.minecraft.net/en-us/eula); ordinary
creation/builds never accept it. Repository-owner consent for this regression test was
recorded on 2026-11-22. No game binaries or worlds are distributed in artifacts.

Runs save redacted logs under `.claude-skills/`, bounded to two million bytes per output
stream. Ctrl-C/cancellation terminates process trees; retries stop after the configured
limit and do not retry missing toolchains or invalid provider output.
