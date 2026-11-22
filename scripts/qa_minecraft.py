#!/usr/bin/env python3
"""Create a NEW project, compile it and inspect its real production artifact."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from builders.scaffold import create
from core.artifacts import inspect
from core.process import Policy, run
from distribution.installer import checked_target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("fabric", "paper", "neoforge", "datapack"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--accept-eula", action="store_true", help="Explicit acceptance of https://www.minecraft.net/eula for this disposable server")
    args = parser.parse_args()
    out = checked_target(args.output)
    out.mkdir(parents=True, exist_ok=False)
    spec = json.loads((ROOT / "examples/briefs/minecraft.json").read_text(encoding="utf-8"))
    spec.update(kind=args.kind, mod_id="workshop_" + args.kind)
    project = out / "project"
    generation = create(spec, project)
    result = {"kind": args.kind, "generation": generation, "ai_generation": "NOT VERIFIED", "runtime": "NOT VERIFIED"}
    try:
        if args.kind == "datapack":
            paths = [p for p in project.rglob("*") if p.is_file() and ("data" in p.relative_to(project).parts or p.name == "pack.mcmeta")]
            for path in paths:
                if path.suffix in (".json", ".mcmeta"):
                    json.loads(path.read_text(encoding="utf-8"))
            tag = json.loads((project / "data/minecraft/tags/function/load.json").read_text())
            for entry in tag["values"]:
                namespace, function = entry.split(":")
                assert (project / f"data/{namespace}/function/{function}.mcfunction").is_file()
            artifact = out / "workshop-datapack-1.21.1.zip"
            with zipfile.ZipFile(artifact, "x", zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(paths):
                    archive.writestr(path.relative_to(project).as_posix(), path.read_bytes())
            result.update(status="passed", evidence_label="STATIC CHECK", artifact=str(artifact), sha256=hashlib.sha256(artifact.read_bytes()).hexdigest())
        else:
            gradle = shutil.which("gradle")
            if not gradle:
                raise FileNotFoundError("Gradle 8.14.3 and Java 21 required")
            build = run([gradle, "--no-daemon", "--console=plain", "build"], project, approved=True, policy=Policy("trusted-local"), timeout=1200)
            (out / "build.log").write_text(build["stdout"] + build["stderr"], encoding="utf-8")
            assert build["status"] == "passed", "Gradle failed; see build.log"
            result.update(status="passed", evidence_label="REAL VERIFIED", build=build["status"], artifacts=inspect(project, "minecraft"))
            if args.kind == "fabric" and args.accept_eula:
                # No existing world or user directory is mounted. Never bind publicly.
                run_dir = project / "run"
                run_dir.mkdir(exist_ok=True)
                (run_dir / "eula.txt").write_text("eula=true\n", encoding="utf-8")
                (run_dir / "server.properties").write_text("server-ip=127.0.0.1\nserver-port=0\nonline-mode=false\nenable-rcon=false\nlevel-name=synthetic-test-world\nlevel-seed=424242\nspawn-protection=0\nview-distance=2\nsimulation-distance=2\nmax-players=1\ngenerate-structures=false\n", encoding="utf-8")
                with (project / "build.gradle").open("a", encoding="utf-8") as stream:
                    stream.write("\nloom { runs { server { vmArg '-Dbuilders.verify=true'; programArg 'nogui' } } }\n")
                server = run([gradle, "--no-daemon", "--console=plain", "runServer"], project, approved=True, policy=Policy("trusted-local"), timeout=600)
                log = server["stdout"] + server["stderr"]
                (out / "server.log").write_text(log, encoding="utf-8")
                expected = f"BUILDERS_RUNTIME_VERIFIED {spec['mod_id']}:{spec['block_id']} {spec['mod_id']}:{spec['item_id']} recipe=present output_count=4"
                assert server["status"] == "passed" and expected in log, "Server registration assertions failed; see server.log"
                result.update(runtime="REAL VERIFIED", runtime_marker=expected, client_visual_test="NOT VERIFIED")
                # Load the actual remapped production JAR too, not only Loom's dev classes.
                production = out / "production-server"
                production.mkdir()
                mods = production / "mods"
                mods.mkdir()
                tested_jar = project / result["artifacts"][0]["path"]
                shutil.copyfile(tested_jar, mods / tested_jar.name)
                api_version = "0.116.18+1.21.1"
                cache = Path.home() / ".gradle/caches/modules-2/files-2.1/net.fabricmc.fabric-api/fabric-api" / api_version
                api = list(cache.glob("*/*.jar"))
                assert len(api) == 1, "Expected one pinned production Fabric API dependency"
                shutil.copyfile(api[0], mods / api[0].name)
                shutil.copyfile(run_dir / "eula.txt", production / "eula.txt")
                shutil.copyfile(run_dir / "server.properties", production / "server.properties")
                launcher_url = "https://meta.fabricmc.net/v2/versions/loader/1.21.1/0.20.1/1.1.2/server/jar"
                with urllib.request.urlopen(launcher_url, timeout=30) as response:
                    launcher_bytes = response.read(2_000_001)
                assert len(launcher_bytes) <= 2_000_000, "Oversized launcher download"
                launcher = production / "fabric-launcher.jar"
                launcher.write_bytes(launcher_bytes)
                java = shutil.which("java")
                assert java, "Java 21 required"
                live = run([java, "-Xmx1G", "-Dbuilders.verify=true", "-jar", str(launcher), "nogui"], production,
                           approved=True, policy=Policy("trusted-local"), timeout=600)
                live_log = live["stdout"] + live["stderr"]
                (out / "production-server.log").write_text(live_log, encoding="utf-8")
                assert live["status"] == "passed" and expected in live_log, "Production JAR server assertions failed"
                result.update(production_runtime="REAL VERIFIED", production_jar_sha256=hashlib.sha256(tested_jar.read_bytes()).hexdigest(),
                              fabric_api_sha256=hashlib.sha256(api[0].read_bytes()).hexdigest(),
                              launcher_url=launcher_url, launcher_sha256=hashlib.sha256(launcher_bytes).hexdigest())
    except (OSError, ValueError, AssertionError, zipfile.BadZipFile) as exc:
        result.update(status="failed", evidence_label="FAILED", reason=str(exc))
    (out / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
