"""Create new projects from validated user briefs without overwriting a workspace."""
from pathlib import Path
import hashlib
import html
import json
import re
import shutil
import struct
import tempfile
import zlib
from distribution.installer import checked_target, is_link

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "builders/templates"
BUILDERS = {"web", "app", "minecraft"}


def validate(spec: dict) -> dict:
    if not isinstance(spec, dict) or spec.get("builder") not in BUILDERS:
        raise ValueError("Specify builder: web, app or minecraft")
    allowed = {"builder", "task", "name", "region", "kind", "mod_id", "block_id", "item_id"}
    if set(spec) - allowed:
        raise ValueError("Unknown brief fields")
    for key, value in spec.items():
        if not isinstance(value, str) or not value.strip() or len(value) > (6000 if key == "task" else 120):
            raise ValueError(f"Invalid brief field: {key}")
        if any(ord(c) < 32 and c not in "\n\t" for c in value):
            raise ValueError("Control characters are not allowed")
    if not spec.get("task", "").strip():
        raise ValueError("A user task is required")
    result = {"name": "Jistič Elektro", "region": "Brno a okolí", **spec}
    if spec["builder"] == "minecraft":
        result = {"kind": "fabric", "mod_id": "copper_workshop", "block_id": "cable_block", "item_id": "voltage_tester", **result}
        if result["kind"] not in ("fabric", "datapack", "paper", "neoforge"):
            raise ValueError("Unsupported Minecraft target")
        for key in ("mod_id", "block_id", "item_id"):
            if not re.fullmatch("[a-z][a-z0-9_]{1,47}", result[key]):
                raise ValueError(f"Invalid Minecraft identifier: {key}")
        if result["block_id"] == result["item_id"]:
            raise ValueError("Block and item must have different identifiers")
    elif any(key in spec for key in ("kind", "mod_id", "block_id", "item_id")):
        raise ValueError("Minecraft fields do not apply to this builder")
    return result


def _png() -> bytes:
    """Original procedural 16px copper checker texture; no third-party image."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    rows = b"".join(b"\0" + b"".join(bytes((187, 91, 53, 255) if (x//4+y//4)%2 else (229, 145, 82, 255))
                                      for x in range(16)) for y in range(16))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 16, 16, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


def minecraft_files(spec: dict) -> dict[str, bytes]:
    mod, block, item = (spec[k] for k in ("mod_id", "block_id", "item_id"))
    target = spec["kind"]
    files = {}
    def put(path, value):
        files[path] = value.encode("utf-8") if isinstance(value, str) else value
    def js(path, value):
        put(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    recipe = {"type": "minecraft:crafting_shaped", "pattern": ["CC", "CC"],
              "key": {"C": {"item": "minecraft:copper_ingot"}},
              "result": {"id": f"{mod}:{block}", "count": 4}}
    if target == "datapack":
        js("pack.mcmeta", {"pack": {"pack_format": 48, "description": spec["name"]}})
        js(f"data/{mod}/recipe/copper_tiles.json", {**recipe, "result": {"id": "minecraft:cut_copper", "count": 4}})
        put(f"data/{mod}/function/check.mcfunction", 'tellraw @a {"text":"Copper workshop datapack loaded","color":"gold"}\n')
        js("data/minecraft/tags/function/load.json", {"values": [f"{mod}:check"]})
        return files
    put("settings.gradle", "pluginManagement { repositories { maven { url = 'https://maven.fabricmc.net/' }; gradlePluginPortal(); mavenCentral(); maven { url = 'https://maven.neoforged.net/releases' } } }\nrootProject.name = '" + mod + "'\n")
    put("gradle.properties", "org.gradle.jvmargs=-Xmx2G\norg.gradle.daemon=false\n")
    if target == "paper":
        put("build.gradle", "plugins { id 'java' }\nversion = '1.0.0'\ngroup = 'dev.builders'\nrepositories { mavenCentral(); maven { url = 'https://repo.papermc.io/repository/maven-public/' } }\ndependencies { compileOnly 'io.papermc.paper:paper-api:1.21.1-R0.1-SNAPSHOT' }\njava { toolchain.languageVersion = JavaLanguageVersion.of(21) }\n")
        put("src/main/resources/plugin.yml", f"name: {mod}\nversion: '1.0.0'\nmain: dev.builders.WorkshopPlugin\napi-version: '1.21'\ncommands:\n  workshop:\n    permission: {mod}.workshop\npermissions:\n  {mod}.workshop:\n    default: op\n")
        put("src/main/java/dev/builders/WorkshopPlugin.java", f'''package dev.builders;
import org.bukkit.command.Command;
import org.bukkit.command.CommandSender;
import org.bukkit.plugin.java.JavaPlugin;
public final class WorkshopPlugin extends JavaPlugin {{
    @Override public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {{
        if (!sender.hasPermission("{mod}.workshop")) return false;
        sender.sendMessage("Copper workshop is ready.");
        return true;
    }}
}}
''')
        return files
    asset = f"src/main/resources/assets/{mod}"
    js(f"{asset}/blockstates/{block}.json", {"variants": {"": {"model": f"{mod}:block/{block}"}}})
    js(f"{asset}/models/block/{block}.json", {"parent": "minecraft:block/cube_all", "textures": {"all": f"{mod}:block/{block}"}})
    js(f"{asset}/models/item/{block}.json", {"parent": f"{mod}:block/{block}"})
    js(f"{asset}/models/item/{item}.json", {"parent": "minecraft:item/generated", "textures": {"layer0": f"{mod}:item/{item}"}})
    js(f"{asset}/lang/en_us.json", {f"block.{mod}.{block}": "Copper Cable Block", f"item.{mod}.{item}": "Voltage Tester"})
    js(f"{asset}/lang/cs_cz.json", {f"block.{mod}.{block}": "Měděný kabelový blok", f"item.{mod}.{item}": "Zkoušečka napětí"})
    put(f"{asset}/textures/block/{block}.png", _png())
    put(f"{asset}/textures/item/{item}.png", _png())
    js(f"src/main/resources/data/{mod}/recipe/{block}.json", recipe)
    if target == "neoforge":
        put("build.gradle", "plugins { id 'java'; id 'net.neoforged.moddev' version '2.0.148' }\nversion = '1.0.0'\ngroup = 'dev.builders'\njava { toolchain.languageVersion = JavaLanguageVersion.of(21) }\nneoForge { version = '21.1.172'; mods { workshop { sourceSet(sourceSets.main) } } }\n")
        put("src/main/resources/META-INF/neoforge.mods.toml", f'''modLoader="javafml"
loaderVersion="[4,)"
license="MIT"
[[mods]]
modId="{mod}"
version="1.0.0"
displayName="Copper Workshop"
[[dependencies.{mod}]]
modId="neoforge"
type="required"
versionRange="[21.1.172,)"
ordering="NONE"
side="BOTH"
[[dependencies.{mod}]]
modId="minecraft"
type="required"
versionRange="[1.21.1,1.21.2)"
ordering="NONE"
side="BOTH"
''')
        put("src/main/java/dev/builders/WorkshopMod.java", f'''package dev.builders;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.BlockItem;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.registries.DeferredRegister;
@Mod("{mod}")
public final class WorkshopMod {{
    private static final DeferredRegister.Blocks BLOCKS = DeferredRegister.createBlocks("{mod}");
    private static final DeferredRegister.Items ITEMS = DeferredRegister.createItems("{mod}");
    private static final java.util.function.Supplier<Block> CABLE = BLOCKS.register("{block}", () -> new Block(BlockBehaviour.Properties.of().strength(3.0F)));
    public WorkshopMod(IEventBus bus) {{
        ITEMS.register("{block}", () -> new BlockItem(CABLE.get(), new Item.Properties()));
        ITEMS.register("{item}", () -> new Item(new Item.Properties()));
        BLOCKS.register(bus);
        ITEMS.register(bus);
    }}
}}
''')
        return files
    put("build.gradle", "plugins { id 'fabric-loom' version '1.10.5' }\nversion = '1.0.0'\ngroup = 'dev.builders'\nrepositories { mavenCentral() }\ndependencies {\n minecraft 'com.mojang:minecraft:1.21.1'\n mappings 'net.fabricmc:yarn:1.21.1+build.3:v2'\n modImplementation 'net.fabricmc:fabric-loader:0.20.1'\n modImplementation 'net.fabricmc.fabric-api:fabric-api:0.116.18+1.21.1'\n}\njava { sourceCompatibility = JavaVersion.VERSION_21; targetCompatibility = JavaVersion.VERSION_21 }\ntasks.withType(JavaCompile).configureEach { options.release = 21 }\n")
    js("src/main/resources/fabric.mod.json", {"schemaVersion": 1, "id": mod, "version": "1.0.0", "name": spec["name"],
       "environment": "*", "entrypoints": {"main": ["dev.builders.WorkshopMod"]},
       "depends": {"fabricloader": ">=0.20.1", "minecraft": "1.21.1", "java": ">=21", "fabric-api": "*"}})
    put("src/main/java/dev/builders/WorkshopMod.java", f'''package dev.builders;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.block.AbstractBlock;
import net.minecraft.block.Block;
import net.minecraft.item.BlockItem;
import net.minecraft.item.Item;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.util.Identifier;
public final class WorkshopMod implements ModInitializer {{
    private static final String ID = "{mod}";
    private static final Block CABLE = new Block(AbstractBlock.Settings.create().strength(3.0f));
    private static final Item TESTER = new Item(new Item.Settings());
    @Override public void onInitialize() {{
        Registry.register(Registries.BLOCK, Identifier.of(ID, "{block}"), CABLE);
        Registry.register(Registries.ITEM, Identifier.of(ID, "{block}"), new BlockItem(CABLE, new Item.Settings()));
        Registry.register(Registries.ITEM, Identifier.of(ID, "{item}"), TESTER);
        // Checks run only on the dedicated test server when explicitly enabled.
        if (Boolean.getBoolean("builders.verify")) ServerLifecycleEvents.SERVER_STARTED.register(server -> {{
            if (Registries.BLOCK.get(Identifier.of(ID, "{block}")) != CABLE) throw new IllegalStateException("Missing block");
            if (Registries.ITEM.get(Identifier.of(ID, "{item}")) != TESTER) throw new IllegalStateException("Missing item");
            var recipe = server.getRecipeManager().get(Identifier.of(ID, "{block}")).orElseThrow(() -> new IllegalStateException("Missing recipe"));
            var output = recipe.value().getResult(server.getRegistryManager());
            if (!output.isOf(CABLE.asItem()) || output.getCount() != 4) throw new IllegalStateException("Invalid recipe output");
            System.out.println("BUILDERS_RUNTIME_VERIFIED " + ID + ":{block} " + ID + ":{item} recipe=present output_count=4");
            server.stop(false);
        }});
    }}
}}
''')
    return files


def create(spec: dict, workspace: Path) -> dict:
    spec = validate(spec)
    bundle = ROOT / "bundle.json"
    if bundle.is_file() and json.loads(bundle.read_text())["builder"] != spec["builder"]:
        raise ValueError("Builder is not included in this standalone runtime")
    workspace = checked_target(workspace)
    # Atomic publication into a NEW directory. Existing even empty directories are protected.
    if workspace.exists():
        raise FileExistsError("Choose a new workspace; existing directories are never overwritten")
    workspace.parent.mkdir(parents=True, exist_ok=True)
    files = {}
    if spec["builder"] == "minecraft":
        files = minecraft_files(spec)
    else:
        base = checked_target(TEMPLATES / spec["builder"])
        for path in base.rglob("*"):
            if is_link(path):
                raise ValueError("Linked template rejected")
            if path.is_file() and not any(p in ("__pycache__", "dist") for p in path.parts) and path.suffix != ".pyc":
                data = path.read_bytes()
                if path.suffix in (".html", ".json"):
                    data = data.replace(b"@@NAME@@", html.escape(spec["name"], quote=True).encode())
                    data = data.replace(b"@@REGION@@", html.escape(spec["region"], quote=True).encode())
                files[path.relative_to(base).as_posix()] = data
    files["builder-brief.json"] = (json.dumps(spec, indent=2, ensure_ascii=False) + "\n").encode()
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}
    manifest = {"schema_version": 1, "builder": spec["builder"], "generator": "deterministic-reference",
                "ai_generated": False, "version": "0.2.0", "files": hashes}
    files["builder-manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    stage = Path(tempfile.mkdtemp(prefix=".builder-stage-", dir=workspace.parent))
    try:
        for rel, data in files.items():
            dest = stage / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        # rename refuses collisions on Windows. On POSIX a concurrently created empty dir
        # is protected by the cooperative exclusive reservation below.
        reservation = workspace.parent / ("." + workspace.name + ".builder-lock")
        with reservation.open("x"):
            pass
        try:
            if workspace.exists():
                raise FileExistsError(workspace)
            stage.rename(workspace)
        finally:
            reservation.unlink()
    finally:
        if stage.exists() and stage.parent.resolve() == workspace.parent.resolve() and not is_link(stage):
            shutil.rmtree(stage)  # generated temporary directory only
    return {"builder": spec["builder"], "workspace": str(workspace), "files": len(files),
            "generation": "deterministic-reference", "ai_generated": False, "verification": "NOT VERIFIED"}
