# Minecraft Builder

Independent skills, executable runtime and deterministic fresh-project generator for
Minecraft Java 1.21.1. Supported reference targets: Fabric, Paper, NeoForge and datapack.
Loader APIs are kept separate. These bounded scaffolds do not prove authenticated AI synthesis.

```bash
python -m distribution.cli install minecraft --target ../skills
python -m core.builder_cli create --spec examples/briefs/minecraft.json --workspace ../new-mod
```

In an installed skill, the launcher is `minecraft-architecture/runtime/builder.py`;
the matching example brief is in that runtime's `examples/briefs/` directory. No other
builder is required. Python 3.11+ runs the generator; builds need Java 21 and Gradle 8.14.3.

The Fabric brief controls mod, block and standalone-item IDs. Outputs include a shaped
recipe, original procedural PNG textures, models/blockstates and English/Czech localization.
The CI script creates a new project, compiles/remaps a JAR, independently inspects it and,
with explicit EULA acceptance, asserts live block/item/recipe registration in a disposable
loopback server. Production-JAR and client-visual scopes are reported separately.

Paper/NeoForge scaffolds have separate build configurations. A datapack gets versioned
metadata, a copper recipe and load function. Static/datapack validation is not a game run.
See the repository's `docs/VERIFICATION.md` for actual outcomes and the compatibility
checklist in `Minecraft/COMPATIBILITY.md` for an existing project.

Run the bundled read-only Cleaner before delivery. Never operate on user worlds or
publish game content automatically. No game binaries or third-party textures are bundled.
