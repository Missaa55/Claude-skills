#!/usr/bin/env python3
"""Real build, HTTP tests, browser screenshots and axe for BOTH generated concepts."""
import argparse
import json
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.pipeline import verify
from core.process import Policy
from scripts.qa_browser import axe_source, load_module


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--simulate-research", choices=("electrical", "footwear"), help="CI fixture only; no external research is claimed")
    args = parser.parse_args()
    if args.simulate_research:
        import runpy
        from builders.designer import design
        fixture = runpy.run_path(str(ROOT / "tests/test_designer.py"))["synthetic_research"](args.simulate_research)
        design("Přístupný návrh s příběhem a přehledným postupem", "Synthetic Design", args.simulate_research, fixture, args.workspace, allow_simulated=True)
    args.output.mkdir(parents=True, exist_ok=False)
    plan = json.loads((args.workspace / "design-comparison.json").read_text(encoding="utf-8"))
    report = {"research": plan["evidence_label"], "analyzed_candidates": plan["analyzed_candidates"],
              "distinct_dimensions": plan["distinct_dimensions"], "checks": [], "screenshots": []}
    source = axe_source()
    computed = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for concept in plan["concepts"]:
            project = (args.workspace / concept["id"]).resolve()
            check = verify(project, "web", approved=True, policy=Policy("trusted-local"))
            (args.output / f"{concept['id']}-build.json").write_text(json.dumps(check, indent=2, ensure_ascii=False), encoding="utf-8")
            if check["status"] != "passed":
                report["checks"].append({"concept": concept["id"], "status": "FAILED", "reason": "Build/HTTP suite failed"})
                continue
            module = load_module("design_" + concept["id"], project / "server.py")
            server = module.make_server(database=args.output / (concept["id"] + "-synthetic.sqlite3"))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            context = browser.new_context(locale="cs-CZ", reduced_motion="reduce")
            try:
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                for device, width, height in (("desktop", 1440, 1000), ("mobile", 390, 844)):
                    page.set_viewport_size({"width": width, "height": height})
                    page.goto(f"http://127.0.0.1:{server.server_port}", wait_until="networkidle")
                    assert page.locator("h1").is_visible()
                    for check_width in (320, width):
                        page.set_viewport_size({"width": check_width, "height": height})
                        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), f"Overflow at {check_width}"
                    page.set_viewport_size({"width": width, "height": height})
                    page.evaluate(source)
                    axe = page.evaluate("async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})")
                    violations = [{"id": v["id"], "nodes": [n["target"] for n in v["nodes"]]} for v in axe["violations"]]
                    assert not violations, json.dumps(violations)
                    name = f"design-{concept['id']}-{device}.png"
                    page.screenshot(path=str(args.output / name), full_page=True, animations="disabled")
                    report["screenshots"].append(name)
                    report["checks"].append({"concept": concept["id"], "device": device, "status": "REAL VERIFIED", "axe_violations": 0, "manual_a11y_items": len(axe["incomplete"])})
                    if device == "desktop":
                        computed.append(page.evaluate("({font:getComputedStyle(document.querySelector('h1')).fontFamily,hero_display:getComputedStyle(document.querySelector('.hero')).display,hero_height:Math.round(document.querySelector('.hero').getBoundingClientRect().height)})"))
                if plan["industry"] == "footwear":
                    page.get_by_role("button", name="Vybrat model Město").click()
                    assert "Město" in page.locator("#selection-status").inner_text()
                if concept["scroll"] == "sticky-story":
                    normal = browser.new_context(reduced_motion="no-preference", viewport={"width": 1440, "height": 1000})
                    try:
                        story_page = normal.new_page()
                        story_page.goto(f"http://127.0.0.1:{server.server_port}", wait_until="networkidle")
                        assert story_page.locator("#postup > h2").evaluate("e=>getComputedStyle(e).position") == "sticky"
                        story_page.evaluate("window.scrollTo({top:document.querySelector('#postup').offsetTop+250,behavior:'instant'})")
                        assert story_page.evaluate("scrollY") > 250
                        report["checks"].append({"concept": concept["id"], "status": "REAL VERIFIED", "normal_scroll": "sticky story; native scrolling", "reduced_motion": "static fallback tested"})
                    finally:
                        normal.close()
                assert not errors, errors
            except Exception as exc:
                report["checks"].append({"concept": concept["id"], "status": "FAILED", "reason": str(exc)})
            finally:
                context.close()
                server.shutdown()
                server.server_close()
                thread.join(5)
        browser.close()
    report["computed_styles"] = computed
    report["measurably_distinct"] = len(computed) == 2 and computed[0]["font"] != computed[1]["font"] and computed[0]["hero_display"] != computed[1]["hero_display"]
    report["status"] = "REAL VERIFIED" if report["measurably_distinct"] and not any(c["status"] == "FAILED" for c in report["checks"]) else "FAILED"
    (args.output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return int(report["status"] == "FAILED")


if __name__ == "__main__":
    raise SystemExit(main())
