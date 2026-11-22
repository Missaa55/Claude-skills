# Fabric Minecraft 1.21.1 real-build fixture

This fixture registers a Workshop Block and BlockItem, adds it to the building-block creative tab, includes a shaped recipe (8 stone around an empty center), blockstate/model/item model and English localization. The block reuses the vanilla stone texture intentionally.

Requires JDK 21 and Gradle 8.14.3. In CI, setup-gradle provides Gradle; locally use `gradle build`. The first build downloads Minecraft, Fabric Loom and dependencies.

This example is a **real source project**. A successful Gradle build demonstrates Java compilation, resource processing and Fabric remapping. It does not demonstrate that the mod has been launched in Minecraft or that the crafting recipe works in-game. Those require a separate game/integration test.

The `tests/test_fabric_fixture.py` checks static asset/recipe structure; it is not a substitute for the Gradle build.
