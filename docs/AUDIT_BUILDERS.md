# Builder audit and verification

Baseline: `6c8ac20966c3bc5f97ad8250b3bc2b42b8db5d40`, inspected on 2026-11-22.
All remote heads fetched; `origin/main` was the only remote branch. No AGENTS.md was present.
The source inventory includes all six skill collections, contracts, router/planner, runtime,
installer, cleaner, tests, documentation, Fabric fixture, and all three workflows.

## Baseline findings

| ID | Severity | Evidence | Required correction |
| --- | --- | --- | --- |
| SEC-01 | High | `distribution/installer.py`: writes files before committing state, no operation lock or rollback | Journal, validated recovery, nonblocking exclusive lock, injected disk-failure tests |
| SEC-02 | High | State only checks its outer shape; relative names can claim another module's or unrelated target files; matching unmanaged content is silently adopted | Strict record types, portable paths, namespace ownership, no adoption |
| SEC-03 | High | `Path.resolve()` hides target symlinks; Windows junctions are not symlinks | Reject reparse points throughout source and destination ancestry |
| SEC-04 | High | `core/runtime.py` inherits host environment, captures unlimited output, logs raw secrets; timeout does not reliably terminate descendants | Scrub environment, bounded streaming, redaction, process-tree cancellation |
| SEC-05 | High | Agent and generated build processes run on host with no enforced isolation | Fail closed for untrusted execution; separately approved, reviewed local checks only |
| QA-01 | High | `core/pipeline.py` calls a project verified after one exit-zero build/test; no artifact validation | Require actual nonempty outputs, independent checks, hashes, explicit verification scope |
| QA-02 | High | No web/application reference, HTTP/database/browser tests or screenshots | Runnable synthetic references and reproducible integration/browser checks |
| MC-01 | High | Only prewritten Fabric example compiled; no new-project or server-registration evidence | New spec-driven project, standalone item, textures, server assertions and actual JAR |
| DIST-01 | Medium | Installed modules contain skills and cleaner, no standalone builder runtime/package | Independent versioned archives with integrity manifests and CLI |
| CLEAN-01 | Medium | Scanner skips resources entirely and only searches four phrases plus backup names | AST/reference/asset/API checks, report limitations, no automatic deletion |
| DOC-01 | Medium | Architecture describes only offline tracker, while later docs describe runtime; skill count stale | Rewrite around actual supported behavior and evidence |
| WIN-01 | Medium | Local baseline: 78 tests, 77 pass, symlink test fails with WinError 1314 | Skip only unsupported symlink creation, add executable junction coverage |

The old green Actions runs establish their stated narrow coverage. They do not establish
agent generation, live Minecraft registration, application authentication, or website quality.
Baseline Windows test run used Python 3.12.14 bundled with the Work runtime. System `python`
was an inactive Windows Store alias. Java 17 was present; Java 21/Gradle/Docker were absent.
WSL Ubuntu could not start (`HCS_E_HYPERV_NOT_INSTALLED`). No system settings were changed.

## Evidence labels

- **REAL VERIFIED**: an actual process or browser ran and the stated assertion passed.
- **SIMULATED**: mocks/fault injection exercised a scenario; no external service proved.
- **STATIC CHECK**: source/structure validation only.
- **NOT VERIFIED**: not run or missing prerequisites.
- **FAILED**: actual check failed; retained as evidence even after a later successful repair.

Final results and limitations are recorded in `VERIFICATION.md`. Deterministic scaffolding
is always identified separately from AI generation. No exit code alone establishes product readiness.
