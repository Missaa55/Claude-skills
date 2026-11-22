# Builder verification and handoff

Date: 2026-11-22. Branch: `codex/builders-runtime-qa`.
[Draft pull request #1](https://github.com/Missaa55/Claude-skills/pull/1) is open for review;
it has not been merged. No public deployment was performed.

**Readiness:** runnable reference generators, independently installed runtimes and
repeatable QA are implemented. General authenticated AI generation through Claude/Codex
is **NOT VERIFIED**. These references are generated deterministically from validated
JSON briefs; they are not claimed to be autonomous AI-created projects.

## Evidence labels

| Label | Meaning |
| --- | --- |
| REAL VERIFIED | The named operation actually ran and its stated assertions passed |
| SIMULATED | Mocked service, injected fault or fixture; not proof of the external system |
| STATIC CHECK | Structure/source/metadata analysis; no runtime or visual claim |
| NOT VERIFIED | Not run or required access/tool is unavailable |
| FAILED | An actual failed check, including historical failures repaired later |

## Commits and CI

| Commit | Change |
| --- | --- |
| [821025ac](https://github.com/Missaa55/Claude-skills/commit/821025ac20278aa69f0e5874b0016ece1b1b24d4) | Lifecycle security, bounded runtime and new brief-driven references |
| [ebea3151](https://github.com/Missaa55/Claude-skills/commit/ebea3151c0b1da4dafa97e4c5d94a9effee1817b) | Standalone runtimes, Cleaner V2, browser QA, macOS path correction |
| [67b14958](https://github.com/Missaa55/Claude-skills/commit/67b1495853803980ee11d574b0f62bd461fa0dfd) | Sector research, two designs, portable Claude image skill and stronger server assertions |
| [f9073cf6](https://github.com/Missaa55/Claude-skills/commit/f9073cf67638f5511dfe33f7a00688516fffb064) | Portable CPU render correction and verified screenshot artifact upload |
| [ec60357b](https://github.com/Missaa55/Claude-skills/commit/ec60357b80dedb5699436564e4ec33f8a6fdd8bf) | Cleaner server/client distinction and unused test import removal |
| [318cc6bd](https://github.com/Missaa55/Claude-skills/commit/318cc6bdb14e18a1dd2c763e2ee7dca4dce1dee8) | Canonical package text across LF/CRLF checkouts; binary assets preserved |

The [complete real QA run for f9073cf6](https://github.com/Missaa55/Claude-skills/actions/runs/45063639699)
passed all eleven jobs: three operating systems, distributions, four Minecraft targets,
the live Fabric server, real browser/Lighthouse checks and optional Blender CPU rendering.
The [subsequent Cleaner regression CI](https://github.com/Missaa55/Claude-skills/actions/runs/45064030202)
also passed all eleven jobs at ec60357b. Package newline normalization has nine passing
local archive/installation tests; its
[final CI at 318cc6bd](https://github.com/Missaa55/Claude-skills/actions/runs/45064666092)
also passed all eleven jobs. The final suite ran 124 tests on each OS: Windows passed
all 124; Linux/macOS passed with the two Windows-specific checks explicitly skipped.
Earlier real evidence is retained below.

| Check | Result | Evidence |
| --- | --- | --- |
| Module lifecycle across Windows/Linux/macOS | REAL VERIFIED | [Final nine module/platform smoke jobs](https://github.com/Missaa55/Claude-skills/actions/runs/45064666164) succeeded |
| Root suites on Windows/Linux/macOS | REAL VERIFIED | [Final QA run](https://github.com/Missaa55/Claude-skills/actions/runs/45064666092): 124 tests per OS, with platform-specific skips as above |
| 43 skill metadata records and registry/contracts | STATIC CHECK | Local validators and [final validator CI](https://github.com/Missaa55/Claude-skills/actions/runs/45064666184) passed |
| Windows final local suite | REAL VERIFIED | 123 tests ran, 122 passed, one symlink-creation test skipped for unavailable privilege; actual junction tests passed; `.artifacts/unit-windows-handoff.log` |
| Final pipeline and image helper regressions | REAL VERIFIED | 14 local tests passed; mocked agent/build/provider cases remain SIMULATED |
| Standalone archive creation | REAL VERIFIED | Four versioned ZIPs built locally with SHA-256 and integrity manifests; independent-runtime tests passed |
| LF/CRLF distribution reproducibility | REAL VERIFIED | Actual archives from both newline variants match within one Python/compression toolchain; binary bytes preserved; all six extracted image-skill files match Linux CI |

## Web, application and designer

`scripts/qa_browser.py` generated new web/app projects, built them, ran their actual HTTP
suites and used Chromium 145.0.7632.6 through Playwright 1.58.0 locally. The successful
local report is `.artifacts/browser-2/report.json`. All eleven named browser checks
passed. Screenshots are real browser captures, not generated mockups.

| Operation | Result | Scope |
| --- | --- | --- |
| Electrical web production build and five HTTP tests | REAL VERIFIED | Actual public-file/security-header checks, valid/invalid form persistence and origins |
| Web browser journeys | REAL VERIFIED | Navigation, menu/Escape, skip link, form submission, invalid values and widths 320/390/768/1440 |
| Form transport error UI | SIMULATED | Playwright aborts the request; actual browser renders the error state |
| App production build and 17 HTTP/database tests | REAL VERIFIED | Login, session/CSRF, roles/technician scope, customer/job/material CRUD, integer prices, migrations, persistence and invalid data |
| App browser journeys | REAL VERIFIED | Wrong password, admin login, customer/job/material creation, total 158020 cents, status update/reload, viewer denial and logout |
| Automated accessibility | REAL VERIFIED | Zero axe WCAG A/AA violations in tested desktop/mobile states; incomplete/manual items remain, no claim of full accessibility certification |
| SEO | STATIC CHECK | Title, description, language, viewport, semantic sections and local demo indexing policy; ranking/real search indexing NOT VERIFIED |
| Lighthouse 12.8.2 | REAL VERIFIED | Actual mobile-default lab run: performance 100, accessibility 100, best practices 100, SEO 100; one local reference page in CI, not a field-traffic guarantee |
| Visual review | REAL VERIFIED | Inspected actual reference and concept screenshots; concepts differ in typography, spacing, structure and artwork; not user acceptance testing |
| Research: electrical | REAL VERIFIED / STATIC CHECK | 32 attempted, 22 successful distinct domains; real HTTPS fetches, static HTML/CSS signals |
| Research: footwear | REAL VERIFIED / STATIC CHECK | 40 attempted, 20 successful distinct domains; real HTTPS fetches, static signals |
| Two concepts in both sectors | REAL VERIFIED | Each built with five HTTP tests; all eight desktop/mobile captures passed overflow/axe checks; fonts and grid/flex hero composition differ; seven of seven design dimensions differ |
| Normal/reduced motion | REAL VERIFIED | Native scrolling and sticky story in normal mode, static reduced-motion fallback |
| Longitudinal market trends and three-year forecast | NOT VERIFIED | Snapshot comparison logic has SIMULATED tests; future taste is explicitly design intent, not a forecast |

Local concept reports are `.artifacts/design-electrical-final-evidence/report.json` and
`.artifacts/design-footwear-final-evidence/report.json`. Each directory contains
`design-a-desktop.png`, `design-a-mobile.png`, `design-b-desktop.png`, and
`design-b-mobile.png`. Their input projects are in `.artifacts/design-INDUSTRY-final/`.
The CI designer run uses **SIMULATED research fixtures** for repeatability; its actual
browser execution is real and must not be confused with the separate local live research.

## Minecraft

[Prior real QA](https://github.com/Missaa55/Claude-skills/actions/runs/45058954354)
created new projects from `examples/briefs/minecraft.json`, rather than reusing the
historical `examples/fabric-1211/` fixture. Java 21 and Gradle 8.14.3 ran in CI.

| Workflow | Result | Evidence boundary |
| --- | --- | --- |
| Fabric 1.21.1 compilation and production JAR | REAL VERIFIED | Registered custom block and standalone item; recipe, models, original PNG textures, en/cs locale; metadata and compiled entrypoint inspection |
| Fabric dedicated development server | REAL VERIFIED | Actual SERVER_STARTED assertions checked block/item/recipe; marker in server.log followed by orderly shutdown |
| Remapped production JAR loaded by standalone Fabric server | REAL VERIFIED | Actual standalone Fabric launch, content/recipe assertions including four output items, orderly shutdown; matching JAR hash below |
| Paper project build/JAR | REAL VERIFIED | Command/permission plugin compiles; live Paper server NOT VERIFIED |
| NeoForge project build/JAR | REAL VERIFIED | Loader project compiles; live NeoForge server NOT VERIFIED |
| Datapack packaging | STATIC CHECK | Format 48, singular directories, valid JSON/function references and ZIP; actual game load NOT VERIFIED |
| Client models/textures and crafting interaction | NOT VERIFIED | Source/resource checks and server recipe existence do not prove rendered client appearance or GUI crafting |
| AI Minecraft generation | NOT VERIFIED | Deterministic scaffold, no authenticated Claude agent run |

The owner explicitly accepted Minecraft EULA for isolated tests. Test servers bind to
loopback, use a new synthetic world, expose no RCON and do not access existing worlds.
Game/server binaries and worlds are not distributed. The run's `fabric-live-server`
artifact contains the actual project JAR, result JSON and logs.

The downloaded production artifact from
[run 45063211642](https://github.com/Missaa55/Claude-skills/actions/runs/45063211642/artifacts/14770651674)
was independently SHA-256 checked. Its `workshop_fabric-1.0.0.jar` is 7804 bytes with
SHA-256 `3d4967d106bd72404488550d6e042b4fcafb79353a5840c8ef125caf86e1b2ab`.
The production log contains
`BUILDERS_RUNTIME_VERIFIED workshop_fabric:cable_block workshop_fabric:voltage_tester recipe=present output_count=4`.
This is registry/recipe assertion evidence, not a claim that a player crafted it in a GUI.

## Claude realistic images and optional graphics

| Operation | Result | Boundary |
| --- | --- | --- |
| Portable `claude-image-studio` ZIP/helper | REAL VERIFIED / STATIC CHECK | Extracted standalone helper executes without a Builder; skill validator passes; setup refuses overwrite and writes no credentials/global settings |
| Native Claude image production | NOT VERIFIED | Skill requires a connected generator; no model is hidden inside the skill |
| Authenticated Claude → HF MCP → image file | NOT VERIFIED | Claude CLI, authenticated HF session and image tool are unavailable here; official configuration is documented, not represented as a completed image run |
| Realistic electrician example | REAL VERIFIED | Actual 1536×1024 PNG generated using ChatGPT's built-in image_gen, inspected visually; explicitly NOT a Claude/HF test |
| Optional original Blender render | REAL VERIFIED | Actual 960×640 CPU Cycles PNG in disposable Ubuntu CI; downloaded, hash-checked and visually inspected; no claim of a realistic person from primitives |
| CC0 sourcing/editing | STATIC CHECK | Source/license/provenance workflow implemented; no third-party asset licensing or editing run claimed |

Example `.artifacts/assets/synthetic-electrician.png` has SHA-256
`1b7eeabe319cc63f691dad7019f7e47a3a3dd81f0899b7b9f914de74284bf700`.
It depicts a fictional worker and is not staff/customer evidence. Account login and free
quota remain prerequisites for the portable HF route; no paid OpenAI API was configured.

The downloaded Linux CI image skill ZIP SHA-256 is
`a58cced248c8e7027383eb62914cfb08edf6ba9c113e54b65da8dd44c35f3d38`.
ZIP bytes can differ between Python/compression-library versions even when every
extracted file is identical. Hashes here identify the named downloaded CI artifact.
Blender's original scene PNG SHA-256 is
`b27332f12785e54700384c13ced8967d290fc876d14d7cfd6b95a86cb35e0a21`.
Its first real CI render failed because the distribution lacked OpenImageDenoise;
explicitly disabling that optional component made the CPU render portable.

## Negative tests and recovery

| Scenario | Result | Method |
| --- | --- | --- |
| Missing CLI/Gradle/Docker | REAL VERIFIED / SIMULATED | Local absent tool diagnosis and fail-closed Docker refusal; adapter missing-tool branches also mocked |
| Invalid brief/config/state/duplicate JSON | REAL VERIFIED | Actual parser/installer rejects before output mutation |
| Corrupt/interrupted archive | REAL VERIFIED | Truncated ZIP rejected; checksum mismatch detected; an actual interrupted network transfer is NOT VERIFIED |
| Provider unavailable/invalid response | SIMULATED | Mock responses, malformed output and exit-zero partial result never establish success |
| Timeout/excessive output/child process | REAL VERIFIED | Actual subprocesses, bounded output and descendant termination, including Windows Job Object |
| Failed build/corrupt JAR | SIMULATED / REAL VERIFIED | Mocked build status plus actual malformed artifact inspection; historical real UI/CI failures retained |
| Disk full | SIMULATED | Injected ENOSPC during writes; rollback assertions; physical filesystem exhaustion NOT VERIFIED |
| Permission failure | REAL VERIFIED / SIMULATED | Actual Windows read-only file failure plus injected cross-platform errors; journal/recovery preserves previous install |
| Repeated/concurrent installation and update | REAL VERIFIED | Temporary targets, real locks, idempotence, changed/unmanaged-file protection and independent uninstall |
| Interrupted install/recovery/repair | REAL VERIFIED / SIMULATED | Real interrupted journal snapshots recover safely; provider repair interruption mocked; actual authenticated-agent interruption NOT VERIFIED |
| Version conflict | REAL VERIFIED / STATIC CHECK | Tampered hashes/state and local edits are rejected; full external dependency-version matrix NOT VERIFIED |

These are focused negative/regression checks, not a large-scale throughput/load test.
Historical **FAILED** evidence: baseline Windows symlink privilege failure; macOS `/var`
alias rejection; first mobile layout overflow; first application select accessibility
label; Ubuntu 26.04 not supported by pinned Playwright browser. Corresponding fixes and
subsequent checks are recorded separately rather than rewriting the failed history.
The first Blender denoiser run and screenshot artifact glob upload also **FAILED**;
both succeeded after the corrections in f9073cf6.

## Actual deliverables and readiness

| Deliverable | Evidence/location |
| --- | --- |
| Standalone Minecraft/App/Web/Image Studio ZIPs | [Final CI packages](https://github.com/Missaa55/Claude-skills/actions/runs/45064666092/artifacts/14770304835), version 0.2.0 with individual SHA-256 sidecars and manifests; downloaded into `.artifacts/handoff/release-packages/` and extracted files compared with Windows output |
| Desktop/mobile web/app and concept screenshots, axe, Lighthouse JSON/HTML | [Browser evidence artifact](https://github.com/Missaa55/Claude-skills/actions/runs/45064030202/artifacts/14770353952), twelve actual PNGs; artifact hash checked after download |
| Original CPU-rendered graphic | [Blender artifact](https://github.com/Missaa55/Claude-skills/actions/runs/45063639699/artifacts/14770296955), actual PNG and metadata |
| Production Fabric JAR and server logs | [Live server artifact](https://github.com/Missaa55/Claude-skills/actions/runs/45063211642/artifacts/14770651674), downloaded local copy `.artifacts/minecraft-production-ci/` |
| Runnable source demos | Fresh `.artifacts/handoff/app/` and `.artifacts/handoff/web/`, built and HTTP-tested; source ZIPs in `.artifacts/handoff/final-packages/elektro-{app,web}-demo.zip`; all source templates/briefs are committed for reproduction |
| Local live-research concept projects/screenshots | `.artifacts/design-{electrical,footwear}-final/` and corresponding `-evidence/` directories |
| Realistic generated example | `.artifacts/assets/synthetic-electrician.png`, exact prompt and separate visual-review/provider records; ChatGPT tool only |
| Security, limitations and installation | This report, [security audit](SECURITY_AUDIT.md), [user guide](USER_GUIDE.cs.md) and [PR](https://github.com/Missaa55/Claude-skills/pull/1) |

CI artifacts have finite GitHub retention; download them before expiry. The committed
scripts/briefs reproduce the operations; external service availability and lab scores
can change. Builds are not represented as bit-for-bit reproducible across all toolchains.

| Builder | Ready within this scope | Remaining gate |
| --- | --- | --- |
| Minecraft | REAL VERIFIED: standalone lifecycle, fresh Fabric/Paper/NeoForge compilation, Fabric server content/recipe assertions | NOT VERIFIED: authenticated AI generation, client visuals and non-Fabric live loading |
| AppBuilder | REAL VERIFIED: standalone reference generation, local app, auth/roles/CRUD/migrations and browser journey | NOT VERIFIED: novel AI-generated architecture and production deployment/security review |
| WebBuilder | REAL VERIFIED: responsive reference, functional form, two distinct directions per tested sector, browser/axe/Lighthouse | NOT VERIFIED: general-purpose novel AI design, representative trend forecasting and authenticated Claude/HF generation |

No Builder is labelled a fully verified general autonomous production developer.

## Reproduction and remaining release gates

See [Czech installation/use guide](USER_GUIDE.cs.md), [security audit](SECURITY_AUDIT.md),
[designer](DESIGNER.md), [pipeline](PIPELINE.md) and [Cleaner V2](../quality/README.md).

```bash
python -m unittest discover -s tests -v
python scripts/validate_skills.py
python scripts/validate_registry.py
python scripts/smoke_modules.py all
python -m distribution.bundle build all --output ../packages
python -m pip install -r requirements-qa.txt
python -m playwright install chromium
python scripts/qa_browser.py --output ../fresh-browser-evidence
```

For Minecraft run `scripts/qa_minecraft.py --kind fabric --output ../fresh-minecraft`
with Java 21/Gradle installed. Only after accepting EULA, add `--accept-eula` for the
isolated server checks. Browser output directories must be new. Live research can fail
safely if fewer than twenty domains respond; report those failures rather than padding
the sample with unvisited sites.

Before describing the builders as general production-ready autonomous tools, complete
an authenticated Claude/Codex sandbox run from a novel brief, verify real container
isolation/credential handling, inspect independent outputs and run interrupted repair.
The current CLI's Docker policy is offline and provides no provider credential/egress
broker; a prepared image alone cannot make a remote AI request work. That integration
must be implemented and reviewed before an authenticated autonomous run is possible.
Claude/HF image generation also needs its own authenticated visual test. Paper/NeoForge/
datapack live loading and Minecraft client visuals remain separate gates. Cleaner's
heuristics, sampled competitor signals and system font selection are useful bounded
features, not comprehensive semantic/visual analysis or proof of AI authorship.

## Changed files

81 paths relative to baseline 6c8ac209:

```text
.gitattributes
.github/workflows/builders-qa.yml
.github/workflows/fabric-e2e.yml
.github/workflows/module-install-smoke.yml
.github/workflows/validate.yml
.gitignore
AppBuilder/README.md
AppBuilder/skills/appbuilder-orchestrator/SKILL.md
Minecraft/README.md
Minecraft/skills/minecraft-architecture/SKILL.md
README.md
WebBuilder/README.md
WebBuilder/skills/claude-image-studio/SKILL.md
WebBuilder/skills/claude-image-studio/references/providers.md
WebBuilder/skills/claude-image-studio/scripts/asset_studio.py
WebBuilder/skills/claude-image-studio/scripts/render_scene.py
WebBuilder/skills/webbuilder-design-system/SKILL.md
WebBuilder/skills/webbuilder-orchestrator/SKILL.md
builders/__init__.py
builders/designer.py
builders/research.py
builders/scaffold.py
builders/templates/app/build.py
builders/templates/app/migrations/001_initial.sql
builders/templates/app/migrations/002_indexes.sql
builders/templates/app/server.py
builders/templates/app/static/app.css
builders/templates/app/static/app.js
builders/templates/app/static/index.html
builders/templates/app/tests/test_api.py
builders/templates/footwear/catalog.js
builders/templates/footwear/index.html
builders/templates/footwear/style.css
builders/templates/web/build.py
builders/templates/web/index.html
builders/templates/web/mark.svg
builders/templates/web/server.py
builders/templates/web/site.js
builders/templates/web/style.css
builders/templates/web/tests/test_http.py
core/artifacts.py
core/builder_cli.py
core/cli.py
core/pipeline.py
core/pipeline_cli.py
core/process.py
core/runtime.py
distribution/README.md
distribution/bundle.py
distribution/cli.py
distribution/installer.py
docs/ARCHITECTURE.md
docs/AUDIT_BUILDERS.md
docs/DESIGNER.md
docs/PIPELINE.md
docs/SECURITY_AUDIT.md
docs/USER_GUIDE.cs.md
docs/VERIFICATION.md
examples/briefs/app.json
examples/briefs/minecraft.json
examples/briefs/web.json
examples/research/electrical-candidates.json
examples/research/footwear-candidates.json
framework/registry.json
quality/README.md
quality/cleaner.py
requirements-qa.txt
scripts/lighthouse.mjs
scripts/qa_browser.py
scripts/qa_designer.py
scripts/qa_minecraft.py
tests/test_bundles.py
tests/test_cleaner.py
tests/test_cleaner_v2.py
tests/test_designer.py
tests/test_image_skill.py
tests/test_installer_security.py
tests/test_pipeline.py
tests/test_process.py
tests/test_reference_projects.py
tests/test_runtime.py
```
