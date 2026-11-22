# Minecraft Development Toolkit

A coordinated set of Agent Skills for Minecraft Java development and operations. Designed for Claude Code and other clients that understand the Agent Skills folder format. **Not** a Minecraft mod, running agent, or MCP server.

## Scope

- Fabric, NeoForge and Paper development
- Datapacks, world generation and resource assets
- Server operations, automated testing and release checks
- AI/MCP integration with explicit permission boundaries
- Architecture and cross-skill handoffs

## How to use

Copy a selected `Minecraft/skills/<skill-name>` directory to your agent's skills directory, e.g. `~/.claude/skills/` for Claude Code or project-local `.agents/skills/` for compatible Codex installations. Do not load incompatible Fabric and NeoForge instructions for the same task unless explicitly designing a multiloader project.

For a Fabric 1.21.1 project, start with `minecraft-architecture`, `minecraft-fabric` and `minecraft-testing`. Pin dependencies using the project's existing build files; no game versions or APIs are assumed compatible without verification.

Validate from the repository root:

```bash
python3 scripts/validate_skills.py
python3 -m unittest discover -s tests -v
```

The validator checks all current skill directories: `skills/`, `Minecraft/skills/`, `Universal/skills/`, and `Applications/skills/`.

## Design

All skills share a simple contract: inspect project and version -> plan -> implement or diagnose -> test -> report evidence. The architecture skill coordinates cross-domain work; the offline workflow tracker in `scripts/workflow.py` records stages but does not execute AI agents.

## Limits

These skills do not guarantee correct builds or working Minecraft gameplay. They have not been validated against a live Minecraft installation. The toolkit is unofficial and not affiliated with Mojang, Microsoft, Anthropic or OpenAI.
