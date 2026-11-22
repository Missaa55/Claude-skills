# Claude Skills — practical development workflows

A collection of reusable development skills and offline tools for reviewing changes, investigating bugs, and improving documentation. All examples are synthetic. No private application code, credentials, customer records, or proprietary datasets are included.

## Modular domains

- [Minecraft](Minecraft/README.md): mods, servers, assets and AI integrations
- [Universal](Universal/README.md): planning, security, testing and performance
- [Applications](Applications/README.md): frontend, APIs, databases, desktop/mobile and deployment
- [AppBuilder](AppBuilder/README.md): architecture, design, quality gates and delivery workflow
- [WebBuilder](WebBuilder/README.md): website research, design, SEO, responsive QA and publishing
- [Framework](framework/README.md): deterministic offline skill routing and registry

```bash
python3 framework/route.py "Build a minecraft fabric mod with a backend api"
```

Routing is advisory; it does not run AI agents or build applications.

## Minecraft development

A dedicated [Minecraft toolkit](Minecraft/README.md) contains 11 coordinated skills for Fabric, NeoForge, Paper, datapacks, world generation, assets, server operations, testing, release management, AI integrations and architecture.

## Included skills

| Skill | Purpose |
| --- | --- |
| [Change Reviewer](skills/change-reviewer/SKILL.md) | Review a patch for correctness, regressions, security, and missing tests |
| [Bug Investigator](skills/bug-investigator/SKILL.md) | Reproduce a bug, isolate its cause, and propose a minimal fix |
| [Documentation Auditor](skills/documentation-auditor/SKILL.md) | Check whether docs match the repository and commands |
| [Workflow Orchestrator](skills/workflow-orchestrator/SKILL.md) | Coordinate review, investigation, tests and documentation with evidence |

## Install

Copy a skill directory into your Claude Code skills directory:

```bash
mkdir -p ~/.claude/skills
cp -R skills/change-reviewer ~/.claude/skills/
```

Alternatively, keep the skill files in your repository and ask your coding assistant to follow their instructions. No API key or paid service is needed for the content of these skills.

## Integrated workflow

The offline workflow tracker records six stages in a JSON file and produces an auditable report. It does not invoke AI models or execute tests itself. See [quick-start](docs/QUICKSTART.md), [architecture](docs/ARCHITECTURE.md), and [roadmap](docs/ROADMAP.md).

```bash
python3 scripts/workflow.py init --task "Investigate a sorting regression" --output workflow.json
python3 scripts/workflow.py report --file workflow.json
```

## Validation

Run the standard-library-only validator:

```bash
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -v
```

The validator checks metadata, required sections, and unsafe credential-like patterns; it is **not** a comprehensive security audit.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please propose narrowly scoped changes, include an example and a test when practical, and never commit secrets or personal information.

## Scope and status

Early development: domain-specific skill collections, an offline routing utility, a workflow tracker, and unit tests. CI status must be checked separately. Skills are guidance, not executable security controls. Compatibility with third-party tools does not imply vendor endorsement.

Licensed under MIT; see [LICENSE](LICENSE).

## Experimental local runtime

The new `core/` package can prepare or explicitly run an installed Claude Code or Codex CLI in a user-selected directory. It is **not sandboxed**, not an autonomous multi-agent builder, and is disabled by default.

```bash
python3 -m core.cli web --provider claude --workspace . --prompt "Review this project"
# Add --execute only if you trust the workspace and authorize the CLI run.
```

Read [architecture research](docs/OPEN_SOURCE_RESEARCH.md) before using the runtime. The web, app and Minecraft products remain independent; only runtime infrastructure is shared.

## Install just one builder

The offline modular installer copies only the selected builder's skill instructions to Claude Code. See [installation details](distribution/README.md).

```bash
python3 -m distribution.cli install minecraft
# Or: python3 -m distribution.cli install app
# Or: python3 -m distribution.cli install web
python3 -m distribution.cli status
python3 -m distribution.cli uninstall minecraft
```

Modules are independently installable and removable; no other builder is required. This is a **skill installer**, not an autonomous builder or a standalone executable package. Run commands from a cloned repository with Python 3.10+.

## AI slop and unnecessary-data review

All three builders now include their own `*-quality-cleaner` skill. The shared offline scanner applies separate web/app/Minecraft heuristics and **never deletes files**. See [Quality Cleaner](quality/README.md).

```bash
python3 -m quality.cleaner web ./site
python3 -m quality.cleaner app ./application
python3 -m quality.cleaner minecraft ./mod
```

Findings require human review; placeholder patterns are not reliable proof of AI authorship, and unused files cannot be safely determined by filename alone.

## Experimental end-to-end builder pipeline

The opt-in pipeline now loads **only** the selected builder's skills, invokes an installed Claude/Codex CLI, runs a predeclared build/test check and can retry failed checks up to three times. It does **not** isolate untrusted code, and generated-project success has not yet been demonstrated. See [pipeline instructions and safety warnings](docs/PIPELINE.md).

```bash
python3 -m core.pipeline_cli web --task "Create a landing page" --workspace ./my-site --provider claude
# Add --execute only in a trusted workspace after reviewing the safety warning.
```
