# Open-source architecture research

Sources inspected 2026-11-22:

- [OpenHands architecture](https://github.com/OpenHands/OpenHands/blob/main/docs/architecture.md): separate frontend, agent server, execution runtime, event-oriented lifecycle.
- [OpenHands SDK design](https://github.com/OpenHands/docs/blob/main/sdk/arch/design.mdx): typed tools, workspace abstraction, isolation tradeoffs.
- [SWE-agent architecture](https://github.com/SWE-agent/SWE-agent/blob/main/docs/background/architecture.md): agent-environment interface and remote/local deployments.
- [SWE-agent ACI](https://github.com/SWE-agent/SWE-agent/blob/main/docs/background/aci.md): constrained editing and concise search feedback.
- [Aider lint and test](https://aider.chat/docs/usage/lint-test.html): feedback from real command exit codes into repair loops.
- [Aider Architect/Editor](https://github.com/Aider-AI/aider/blob/main/aider/website/_posts/2024-09-26-architect.md): separate planning and editing responsibilities.

## Local design decisions

- Three product domains (web, app, minecraft) remain independent.
- Shared core provides optional CLI adapter, execution logs, and permission gates.
- The first implementation is an opt-in local provider process launcher; it does not yet implement an autonomous repair loop.
- Host working directory restriction is **not** a security boundary. Untrusted code needs OS/container isolation.
- Provider CLIs must be installed and authenticated by the user. Their behavior, permissions, and pricing depend on the installed version.
- No third-party code was imported from the projects listed above.

## Next research-backed milestones

1. Provider capability/version negotiation and noninteractive approval handling.
2. Explicit Docker/VM sandbox with network and filesystem policies.
3. Structured agent events, resumable runs, cancellation and secret redaction.
4. Real test runner with evidence artifacts and capped repair loops.
5. Independent builder-specific templates, toolchains and end-to-end benchmarks.
