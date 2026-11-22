#!/usr/bin/env python3
"""Real install -> inspect -> execute bundled cleaner -> uninstall smoke test.

Runs CLI subprocesses in a temporary, disposable directory. No AI account,
credentials, network access, external build toolchain or destructive user files.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
from_module = {
    "minecraft": ("Minecraft/skills", "minecraft-quality-cleaner", "Mod.java", "package examplemod;"),
    "app": ("AppBuilder/skills", "appbuilder-quality-cleaner", "app.py", "# TODO: implement"),
    "web": ("WebBuilder/skills", "webbuilder-quality-cleaner", "index.html", "Unleash the power"),
}

def call(*parts, cwd=ROOT):
    result = subprocess.run([sys.executable, *parts], cwd=cwd, capture_output=True,
                            text=True, check=False, timeout=45)
    if result.returncode:
        raise AssertionError(
            f"Command {parts} failed with {result.returncode}:\n{result.stdout}\n{result.stderr}")
    return json.loads(result.stdout)

def run(module):
    source_dir, cleaner_skill, demo_name, demo_content = from_module[module]
    source = ROOT / source_dir
    expected_skills = {p.name for p in source.iterdir() if p.is_dir()}
    assert expected_skills, f"No skills in {source}"
    with tempfile.TemporaryDirectory(prefix=f"claude-skills-smoke-{module}-") as temp:
        sandbox = Path(temp)
        target = sandbox / "claude" / "skills"
        project = sandbox / "sample-project"
        project.mkdir()
        demo = project / demo_name
        demo.write_text(demo_content, encoding="utf-8")
        backup = project / "old.bak"
        backup.write_text("must not delete", encoding="utf-8")
        protected = project / "resources"
        protected.mkdir()
        (protected / "old.bak").write_text("protected content", encoding="utf-8")
        original = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in project.rglob("*") if p.is_file()}

        installed = call("-m", "distribution.cli", "install", module,
                         "--target", str(target))
        assert installed["module"] == module
        assert installed["files"] > 0
        assert call("-m", "distribution.cli", "status", "--target",
                    str(target))["installed"] == [module]
        actual_skills = {p.parent.name for p in target.glob("*/SKILL.md")}
        assert actual_skills == expected_skills, (
            f"{module} leaked other builders or missed skills: {actual_skills ^ expected_skills}")

        cleaner = target / cleaner_skill / "scripts" / "cleaner.py"
        assert cleaner.is_file(), "The installed module does not ship its quality scanner"
        assert cleaner.read_bytes() == (ROOT / "quality/cleaner.py").read_bytes()
        report = call(str(cleaner), module, str(project), cwd=sandbox)
        assert report["deleted_files"] == 0
        types = {f["kind"] for f in report["findings"]}
        assert {"slop_candidate", "cleanup_candidate"} <= types, report
        assert not any(f["path"].startswith("resources/") for f in report["findings"])

        # Running a dry-run checks the correct builder's skill context is readable
        # without launching an agent or contacting provider services.
        dry = call("-m", "core.pipeline_cli", module, "--task",
                   f"Create a sample {module} project", "--workspace", str(project),
                   "--provider", "claude")
        assert dry["status"] == "dry_run"
        assert dry["context_characters"] > 0

        # Reinstall is idempotent and does not bring other modules.
        repeated = call("-m", "distribution.cli", "install", module,
                        "--target", str(target))
        assert repeated["files"] == installed["files"]
        assert {p.parent.name for p in target.glob("*/SKILL.md")} == expected_skills

        removed = call("-m", "distribution.cli", "uninstall", module,
                       "--target", str(target))
        assert removed["removed"] == installed["files"]
        assert call("-m", "distribution.cli", "status", "--target",
                    str(target))["installed"] == []
        leftovers = sorted(p.relative_to(target).as_posix() for p in target.rglob("*"))
        assert leftovers == [], f"Installation left files behind: {leftovers}"

        after = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in project.rglob("*") if p.is_file()}
        assert original == after, "Scanner or installation mutated sample-project files"

        return {"module": module, "result": "PASS",
                "installed_skill_count": len(actual_skills),
                "installed_file_count": installed["files"],
                "cleaner_findings": len(report["findings"]),
                "dry_run": "PASS", "removed_files": removed["removed"],
                "leftovers": leftovers, "sample_project_unchanged": True}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", choices=[*from_module, "all"])
    args = parser.parse_args()
    selected = [args.module] if args.module != "all" else ["minecraft", "app", "web"]
    for module in selected:
        print(json.dumps(run(module), ensure_ascii=False))

if __name__ == "__main__":
    main()
