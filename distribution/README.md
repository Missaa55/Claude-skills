# Independent module installation

This installer copies **only** the selected builder's `SKILL.md` files into a Claude Code skill directory. It is offline and uses Python standard library only. No Minecraft files are installed when selecting web or app, and vice versa.

From a checkout of this repository:

```bash
python3 -m distribution.cli install minecraft
python3 -m distribution.cli install app
python3 -m distribution.cli install web
python3 -m distribution.cli status
python3 -m distribution.cli uninstall web
```

To install into a test directory, add `--target /path/to/skills`. By default the target is `~/.claude/skills`. Run from the repository root.

The installation state is tracked in `.claude-skills-install.json` in the target directory. Updates refuse to overwrite user-modified or unmanaged files. Uninstall refuses to remove modified files. Multiple modules can coexist and be uninstalled independently.

**Scope:** These commands install instruction skills, not a standalone web/app/Minecraft generator, runtime, or third-party toolchains. To use the experimental CLI runtime, follow the separate `core/` instructions. Provider CLI installation and authentication are separate.
