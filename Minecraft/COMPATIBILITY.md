# Compatibility checklist

Before generating code, record these fields from the target project:

| Field | Required evidence |
| --- | --- |
| Minecraft version | Build properties or server manifest |
| Loader / server API | Fabric, NeoForge, Paper, vanilla or other |
| Java version | Gradle toolchain or runtime configuration |
| Mappings / API version | Dependency lock or build files |
| Client vs dedicated server | Entrypoint and dependency analysis |
| Test strategy | JUnit, GameTest, MockBukkit, data validator, manual game test |
| Release destination | Explicit user choice |

Do not use Minecraft 26.x examples as proof that code works on 1.21.x. Treat Fabric, NeoForge and Paper as separate APIs. For existing worlds, back up before migration.
