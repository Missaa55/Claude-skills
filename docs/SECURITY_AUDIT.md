# Security audit — implemented boundaries and remaining risks

Date: 2026-11-22. Baseline findings and severity are in [AUDIT_BUILDERS.md](AUDIT_BUILDERS.md).
This is a source review with executable regression evidence, not an independent
penetration-test certification. Exact runs and artifacts are in [VERIFICATION.md](VERIFICATION.md).
All application/customer/game-world data used for tests is synthetic.

## Findings addressed

| Baseline issue | Correction | Evidence and boundary |
| --- | --- | --- |
| High: traversal and forged installation state | Portable relative paths, exact module skill ownership, strict types/digests, duplicate JSON key rejection; full journal validation before writes | REAL VERIFIED: malformed records/traversals fail before mutation; outside sentinel survives |
| High: links and Windows junctions | Reject symlinks/reparse points in source and destination ancestors; normalize only verified root-owned macOS system aliases | REAL VERIFIED: actual Windows junction tests; Linux/macOS link coverage in CI; Windows symlink creation alone may skip without privilege |
| High: partial writes and unsafe removal | Per-target exclusive lock; durable before/after journal; atomic writes; exception rollback; next-operation recovery; hashes protect subsequent user edits | REAL VERIFIED: interrupted-state recovery, idempotence, concurrent-lock rejection, update/uninstall foreign-file protection; disk-full exception is SIMULATED |
| High: environment/log exposure and runaway children | Argument arrays without shell; allowlisted environment and disposable home; stdin prompt; bounded streams; token redaction; timeout/cancellation of process tree | REAL VERIFIED: actual process, injection-string, environment, output limit, descendant and cancellation tests; redaction has finite patterns |
| High: untrusted host execution | Default Docker-only execution with no silent host fallback; preinstalled digest-pinned image, nonroot, read-only root, no network, no capabilities, resource bounds, workspace-only mount | STATIC CHECK/SIMULATED for Docker command policy; REAL VERIFIED for refusal on this host without Docker; actual container isolation NOT VERIFIED |
| High: exit-zero treated as verification | Nonempty test suite, independent required-file checks/hashes and JAR metadata/compiled entrypoint checks; bounded repair attempts; explicit verification scope | REAL VERIFIED for reference builds/HTTP/browser/server checks; SIMULATED agent responses and build failures; corrupt JAR cannot be accepted |
| Medium: destructive quality cleanup | Read-only scan, bounded files/bytes, no link traversal, no apply/delete endpoint; narrow proposal has reasons, hashes, diff and reverse diff | REAL VERIFIED scanner/proposal tests; STATIC CHECK findings remain review candidates |

The macOS `/var` system-alias failure was caught by real CI and fixed without permitting
arbitrary user symlinks. An actual Windows read-only destination failure now rolls back
and can recover after the permission restriction is removed. Source ownership checks
also reject unmanaged files even when their bytes match an installation payload.

## Application and web reference

The application uses salted scrypt passwords, hashed expiring session tokens, HttpOnly
SameSite cookies, CSRF checks, same-origin/Host validation, role and assigned-job scope,
parameterized SQL, bounded JSON bodies and integer-cent calculations. Migrations are
transactional and checksummed. No shared default password is supplied. Real HTTP tests
cover unauthorized CRUD, viewer denial, technician scope, invalid input, injection strings,
session lifecycle, migration consistency, materials and price totals.

The web server serves an explicit public-file allowlist. Form writes require same-origin
JSON with size/type validation and a per-client rate limit. Responses include CSP,
nosniff, Referrer-Policy and framing restrictions. Form data is stored locally; no external
mail/provider is invoked. Both servers bind to loopback. TLS, Secure cookies over HTTPS,
account recovery, production secrets, backup operations and Internet deployment are outside
this reference's verified scope. Do not expose the development HTTP server publicly.

No known critical issue was observed in the reviewed reference scope. This statement is
not proof that all bugs or vulnerabilities are absent. No dependency advisory database
or third-party penetration test is represented as completed.

## Research, image tools and external content

Research accepts public HTTPS endpoints, checks all resolved IPs against private/reserved
space, pins an allowed IP while retaining TLS hostname verification, and revalidates each
redirect. Per-site process deadlines bound slow DNS/headers/body handling. Responses and
CSS reads have size/count limits. Remote JavaScript is not executed; certificates are not
ignored. Real sector scans and mocked SSRF/timeout cases are reported separately.

Competitor HTML/CSS and downloaded metadata are untrusted data, not agent instructions.
Do not include secrets, production endpoints or private documents in research/image prompts.
Claude Image Studio requires discovery of an actually connected tool and stops at exhausted
free quota. The skill cannot bypass provider authentication or make a paid action authorized.
The metadata helper records hashes/headers only; it does not certify image authenticity,
copyright, releases or visual quality. CC0 claims require original source/license URLs.
The optional Blender script creates its own scene with factory startup and disabled
auto-execution; no downloaded `.blend` scripts or third-party add-ons are executed.

## Residual limitations and release gates

| Severity | Remaining concern | Required next evidence |
| --- | --- | --- |
| High | Authenticated Claude/Codex sandbox generation has not run; the CLI's offline Docker policy has no provider credential/egress broker | Implement/review that integration first, then run an authenticated disposable session with independently checked outputs and interrupted repair |
| High for public deployment | Reference HTTP apps are local demonstrations, not a hardened hosted service | Deployment-specific TLS/session/account/backup review and integration tests before approval |
| Medium | Path checks are not a kernel-enforced defense against a malicious same-user process racing every filesystem operation | Use private, access-controlled installation/workspace directories; do not share them with hostile processes |
| Medium | Pattern-based redaction cannot recognize every possible secret or sensitive natural-language output | Pass no unnecessary secrets; inspect logs before publishing; provider-specific redactors when a provider is actually integrated |
| Medium | Docker shares the host kernel; untrusted agents and privileged Docker access require a maintained environment | Verify the actual environment and consider stronger VM isolation for hostile inputs |
| Medium | Paper snapshot dependency and mutable remote services affect repeatability | Record resolved dependency/artifact hashes; use a verified immutable mirror for stronger reproducibility |
| Medium | Cleaner dependency analysis is literal/static and cannot resolve all dynamic imports/assets | Manual review and language/tool-specific analysis before applying any proposal |
| Low | Package SHA-256 detects corruption, not publisher identity | Compare with trusted CI; signed releases are not implemented |

No production systems, personal worlds, private user data or paid image services were
used. The draft PR is not merged and no public application was deployed. Runtime safety
limits do not make an untrusted model response trustworthy; verification remains a
separate, bounded operation whose exact scope must be reported.
