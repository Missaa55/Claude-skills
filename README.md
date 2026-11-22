# Claude Skills — independent development builders

Three independently installable builders with executable runtimes, portable skills,
brief-driven reference projects, read-only quality analysis and reproducible QA.
Requires Python 3.11+. The runtime/reference web/app projects use the standard library.
Browser QA additionally uses Playwright. Minecraft compilation requires Java 21 and Gradle 8.14.3.

| Builder | Implemented reference | Verification boundary |
| --- | --- | --- |
| Minecraft | New Fabric 1.21.1 mod with block, item, recipe, original textures and two locales; Paper/NeoForge and datapack scaffolds | Real compilation/JAR inspection and Fabric dedicated-server assertions; client visuals are separate |
| AppBuilder | SQLite job manager, sessions, three roles, customers, jobs, materials, integer-cent calculations and REST API | Real HTTP/database suites and browser journeys; loopback reference, not a production hosting stack |
| WebBuilder | Responsive electrical-services site and two-concept designer for electrical/footwear briefs | Real browser screenshots, navigation/forms, responsive checks and axe; research signals are static observations |

**Generation is currently deterministic and explicitly labelled. Authenticated autonomous
Claude/Codex project generation is NOT VERIFIED.** Provider adapters and bounded repair
orchestration exist, but untrusted execution fails closed without a prepared Docker environment.
See the [evidence and remaining limitations](docs/VERIFICATION.md).

## Start from a fresh brief

```bash
python -m core.builder_cli create --spec examples/briefs/web.json --workspace ../new-site
# Review the generated source before approving host execution:
python -m core.builder_cli check web --workspace ../new-site --execute --trusted-local
python ../new-site/server.py --port 8080
```

Use `app.json` or `minecraft.json` for the other builders. Existing directories are
never overwritten. `builder-manifest.json` records source hashes and generation provenance.
The application initializes its demo user explicitly and generates a fresh password:

```bash
python ../new-app/server.py init --demo
python ../new-app/server.py serve --port 8787
```

## Research and two distinct design directions

```bash
python -m core.builder_cli research --candidates examples/research/electrical-candidates.json --output research.json
python -m core.builder_cli design --industry electrical --name "Jistič Elektro" --task "Web elektro firmy s přehledným postupem realizace" --research research.json --workspace ../two-designs
```

The designer requires **20 successfully inspected distinct domains**, dated within seven days.
Blocked/invalid-TLS sources are excluded. Each concept has its own typography, palette,
composition and visual language; at least five of seven dimensions must differ. Native
scrolling and reduced motion remain supported. A three-year horizon is a **design intent**,
not a forecast. See [designer details](docs/DESIGNER.md).

## Install one builder or any combination

```bash
python -m distribution.cli install minecraft --target ../test-skills
python -m distribution.cli install app --target ../test-skills
python -m distribution.cli install web --target ../test-skills
python -m distribution.cli status --target ../test-skills
python -m distribution.cli update web --target ../test-skills
python -m distribution.cli uninstall web --target ../test-skills
```

Each installation includes its own executable runtime inside the orchestrator/architecture
skill's `runtime/` directory and a standalone Cleaner. Use `--client codex` for
`~/.agents/skills`, or the default Claude directory `~/.claude/skills`.
User edits and unmanaged files are protected; updates/removal are journalled and locked.
See [installation and independent ZIP packages](distribution/README.md) and the
[Czech user guide](docs/USER_GUIDE.cs.md).

## Quality and development

```bash
python -m quality.cleaner web ../new-site
python -m quality.cleaner app ../new-app --proposal
python scripts/validate_skills.py
python scripts/validate_registry.py
python -m unittest discover -s tests -v
python scripts/smoke_modules.py all
```

Cleaner findings are review candidates, not proof of AI origin. It never applies changes
or deletes files. See [Cleaner V2](quality/README.md), [security audit](docs/SECURITY_AUDIT.md),
[architecture](docs/ARCHITECTURE.md), [pipeline](docs/PIPELINE.md) and [technical audit](docs/AUDIT_BUILDERS.md).
The older dated audit/install reports preserve historical evidence and are superseded
for current behavior by `docs/VERIFICATION.md`.

Licensed under MIT. Third-party sites, tools and game platforms do not endorse this project.
