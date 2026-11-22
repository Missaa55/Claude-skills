"""Static contract checks; Gradle compilation is verified separately in CI."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "examples" / "fabric-1211"
MOD = "claudeskills_block"
RES = ROOT / "src/main/resources"

class FabricFixtureTests(unittest.TestCase):
    def test_version_and_java(self):
        props = (ROOT / "gradle.properties").read_text()
        self.assertIn("minecraft_version=1.21.1", props)
        self.assertIn("options.release = 21", (ROOT / "build.gradle").read_text())

    def test_entrypoint_and_registration(self):
        meta = json.loads((RES / "fabric.mod.json").read_text())
        self.assertEqual(meta["id"], MOD)
        self.assertEqual(meta["depends"]["minecraft"], "1.21.1")
        java = (ROOT / "src/main/java/dev/claudeskills/ExampleMod.java").read_text()
        self.assertIn("Registry.register(Registries.BLOCK", java)
        self.assertIn("Registry.register(Registries.ITEM", java)
        self.assertIn("onInitialize()", java)

    def test_recipe(self):
        recipe = json.loads((RES / f"data/{MOD}/recipe/workshop_block.json").read_text())
        self.assertEqual(recipe["type"], "minecraft:crafting_shaped")
        self.assertEqual(recipe["pattern"], ["SSS", "S S", "SSS"])
        self.assertEqual(recipe["key"]["S"], "minecraft:stone")
        self.assertEqual(recipe["result"]["id"], f"{MOD}:workshop_block")

    def test_asset_references(self):
        blockstate = json.loads((RES / f"assets/{MOD}/blockstates/workshop_block.json").read_text())
        model = blockstate["variants"][""]["model"]
        self.assertEqual(model, f"{MOD}:block/workshop_block")
        self.assertTrue((RES / f"assets/{MOD}/models/block/workshop_block.json").is_file())
        item = json.loads((RES / f"assets/{MOD}/models/item/workshop_block.json").read_text())
        self.assertEqual(item["parent"], model)
        lang = json.loads((RES / f"assets/{MOD}/lang/en_us.json").read_text())
        self.assertIn(f"block.{MOD}.workshop_block", lang)

if __name__ == "__main__":
    unittest.main()
