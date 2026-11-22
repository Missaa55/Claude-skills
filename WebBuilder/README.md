# WebBuilder for Claude

Independent runtime and portable skills for responsive sites, evidence-based QA and a
two-direction designer. The included electrical-services website has actual navigation,
responsive layouts and a synthetic enquiry form persisted locally in SQLite.

```bash
python -m core.builder_cli create --spec examples/briefs/web.json --workspace ../new-site
python -m core.builder_cli check web --workspace ../new-site --execute --trusted-local
python ../new-site/server.py --port 8080
```

The designer inspects at least 20 successful distinct candidate domains and produces
two independent projects with different fonts, palette, composition and graphic language.
Supported content profiles are electrical services and footwear. A date/URL/hash report
backs current HTML/CSS observations; three-year durability is a design intent, not a forecast.
See the repository's `docs/DESIGNER.md` for commands and limits.

`claude-image-studio` is a separately portable skill for actual image assets. Its default
no-paid-API route is a connected Hugging Face MCP image tool, so the PC needs no dedicated
GPU. Account authorization, internet and available provider quota are prerequisites.
It includes provenance/setup helpers and an optional original Blender scene script;
no model weights, Blender application or paid API key is bundled. Read that skill's
provider reference for the current Claude setup and model-license checks.

Installation: `python -m distribution.cli install web`. The complete installed launcher is
`webbuilder-orchestrator/runtime/builder.py`; the Cleaner and image skill also work separately.
No AppBuilder/Minecraft module is required. Use the bundled standalone ZIP if no checkout exists.

The generator/designer are deterministic reference implementations. Arbitrary authenticated
Claude/Codex synthesis and Claude/HF image generation require separate live verification.
Sites are loopback demos until deployment is explicitly approved. No fake reviews, actual
customer data, payment processing or email delivery are included.
