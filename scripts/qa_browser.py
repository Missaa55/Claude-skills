#!/usr/bin/env python3
"""Real Chromium journeys, axe accessibility, responsive screenshots and timing."""
import argparse
import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import sys
import tarfile
import threading
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from builders.scaffold import create
from core.pipeline import verify
from core.process import Policy, run
from distribution.installer import checked_target


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def axe_source():
    # Fetch exact published package and verify its SRI before reading one file;
    # never extract or execute package install scripts.
    with urllib.request.urlopen("https://registry.npmjs.org/axe-core/4.10.3", timeout=30) as response:
        metadata = json.load(response)
    distribution = metadata["dist"]
    url = distribution["tarball"]
    if not url.startswith("https://registry.npmjs.org/axe-core/"):
        raise ValueError("Unexpected axe registry URL")
    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read(5_000_001)
    if len(data) > 5_000_000:
        raise ValueError("Oversized axe package")
    expected = "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode()
    if distribution["integrity"] != expected:
        raise ValueError("Axe package integrity mismatch")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        return archive.extractfile("package/axe.min.js").read().decode()


def main():
    from playwright.sync_api import sync_playwright, expect
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--axe", type=Path)
    parser.add_argument("--lighthouse-deps", type=Path, help="node_modules containing lighthouse and chrome-launcher")
    args = parser.parse_args()
    out = checked_target(args.output)
    out.mkdir(parents=True, exist_ok=False)
    report = {"evidence_label": "REAL VERIFIED", "checks": [], "screenshots": [],
              "ai_generation": "NOT VERIFIED", "lighthouse": "NOT VERIFIED", "browser": None}
    servers, threads = [], []
    def record(name, function):
        try:
            details = function()
            report["checks"].append({"name": name, "status": "REAL VERIFIED", "details": details})
            return True
        except Exception as exc:
            report["checks"].append({"name": name, "status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
            return False
    def start(server):
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        servers.append(server)
        threads.append(thread)
        return f"http://127.0.0.1:{server.server_port}"
    try:
        source = args.axe.read_text(encoding="utf-8") if args.axe else axe_source()
        for builder in ("web", "app"):
            spec = json.loads((ROOT / f"examples/briefs/{builder}.json").read_text(encoding="utf-8"))
            create(spec, out / builder)
            checked = verify(out / builder, builder, approved=True, policy=Policy("trusted-local"))
            (out / f"{builder}-build.json").write_text(json.dumps(checked, ensure_ascii=False, indent=2), encoding="utf-8")
            if checked["status"] != "passed":
                raise AssertionError(f"{builder} build/integration failed; see build report")
        web_module = load_module("web_reference", out / "web/server.py")
        web_url = start(web_module.make_server(database=out / "web-test.sqlite3"))
        app_module = load_module("app_reference", out / "app/server.py")
        database = out / "app-test.sqlite3"
        app_module.migrate(database)
        password = "Synthetic-browser-only-passphrase7!"
        app_module.create_user(database, "browser_admin", password, "admin")
        app_module.create_user(database, "browser_viewer", password, "viewer")
        app_url = start(app_module.make_server(database))
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            report["browser"] = {"engine": "Chromium", "version": browser.version}
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, locale="cs-CZ", reduced_motion="reduce")
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.add_init_script("window.__lcp=0;new PerformanceObserver(l=>{for(const e of l.getEntries())window.__lcp=e.startTime}).observe({type:'largest-contentful-paint',buffered:true})")
            def screenshot(name):
                page.screenshot(path=str(out / name), full_page=True, animations="disabled")
                report["screenshots"].append(name)
            def audit(name):
                page.evaluate(source)
                result = page.evaluate("async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})")
                violations = [{"id": v["id"], "impact": v["impact"], "help": v["help"], "nodes": [n["target"] for n in v["nodes"]]} for v in result["violations"]]
                (out / f"axe-{name}.json").write_text(json.dumps({"violations": violations, "incomplete": len(result["incomplete"]), "passes": len(result["passes"])}, indent=2), encoding="utf-8")
                assert not violations, json.dumps(violations, ensure_ascii=False)
                return {"axe": "4.10.3", "automated_violations": 0, "manual_review_items": len(result["incomplete"])}
            def web_desktop():
                response = page.goto(web_url, wait_until="networkidle")
                assert response.status == 200
                assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
                expect(page.get_by_role("heading", level=1)).to_be_visible()
                assert page.title().startswith("Jistič Elektro")
                assert page.locator('meta[name="description"]').get_attribute("content")
                for link, target in (("Služby", "#sluzby"), ("Reference", "#reference"), ("Jak pracujeme", "#postup"), ("Probrat zakázku", "#kontakt")):
                    page.get_by_role("navigation").get_by_role("link", name=link).click()
                    expect(page).to_have_url(web_url + "/" + target)
                    expect(page.locator(target)).to_be_in_viewport()
                page.goto(web_url, wait_until="networkidle")
                page.keyboard.press("Tab")
                expect(page.get_by_role("link", name="Přejít na obsah")).to_be_focused()
                page.evaluate("document.activeElement.blur()")
                screenshot("web-desktop.png")
                return page.evaluate("({lcp_ms:window.__lcp,resources:performance.getEntriesByType('resource').length,transferred_bytes:performance.getEntriesByType('resource').reduce((a,r)=>a+r.transferSize,0)})")
            record("web-desktop-navigation-seo-keyboard", web_desktop)
            record("web-desktop-accessibility", lambda: audit("web-desktop"))
            def web_mobile():
                for width in (320, 390, 768, 1440):
                    page.set_viewport_size({"width": width, "height": 844})
                    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), f"Horizontal overflow at {width}px"
                page.set_viewport_size({"width": 390, "height": 844})
                page.goto(web_url, wait_until="networkidle")
                menu = page.get_by_role("button", name="Menu")
                menu.click()
                expect(menu).to_have_attribute("aria-expanded", "true")
                page.keyboard.press("Escape")
                expect(menu).to_be_focused()
                expect(menu).to_have_attribute("aria-expanded", "false")
                menu.click()
                page.get_by_role("navigation").get_by_role("link", name="Služby").click()
                expect(menu).to_have_attribute("aria-expanded", "false")
                page.goto(web_url, wait_until="networkidle")
                screenshot("web-mobile.png")
                return {"widths_without_overflow": [320, 390, 768, 1440]}
            record("web-responsive-menu", web_mobile)
            record("web-mobile-accessibility", lambda: audit("web-mobile"))
            def web_form():
                form = page.locator("#enquiry")
                form.get_by_role("button").click()
                assert not form.evaluate("f=>f.checkValidity()")
                form.get_by_label("Jméno", exact=True).fill("Syntetický Test")
                form.get_by_label("E-mail", exact=True).fill("browser@example.invalid")
                form.get_by_label("Co potřebujete vyřešit?").fill("Pouze syntetická testovací poptávka pro ověření formuláře.")
                form.get_by_role("checkbox").check()
                form.get_by_role("button").click()
                expect(page.locator("#form-status")).to_contain_text("je uložená")
                connection = sqlite3.connect(out / "web-test.sqlite3")
                try:
                    assert connection.execute("SELECT COUNT(*) FROM enquiries").fetchone()[0] == 1
                finally:
                    connection.close()
                form.get_by_label("Jméno", exact=True).fill("Syntetický Výpadek")
                form.get_by_label("E-mail", exact=True).fill("failure@example.invalid")
                form.get_by_label("Co potřebujete vyřešit?").fill("Syntetický požadavek při simulovaném síťovém výpadku.")
                form.get_by_role("checkbox").check()
                page.route("**/api/enquiries", lambda route: route.abort())
                form.get_by_role("button").click()
                expect(page.locator("#form-status")).to_contain_text("Spojení se nezdařilo")
                page.unroute("**/api/enquiries")
                return {"persisted_enquiries": 1, "invalid_form": "REAL VERIFIED", "network_failure": "SIMULATED"}
            record("web-form-persistence-and-errors", web_form)
            def app_journey():
                page.set_viewport_size({"width": 1440, "height": 1000})
                page.goto(app_url, wait_until="networkidle")
                login = page.locator("#login-form")
                login.get_by_label("Uživatelské jméno").fill("browser_admin")
                login.get_by_label("Heslo", exact=True).fill("incorrect-synthetic")
                login.get_by_role("button").click()
                expect(page.locator("#login-error")).to_contain_text("Nesprávné")
                login.get_by_label("Heslo", exact=True).fill(password)
                login.get_by_role("button").click()
                expect(page.locator("#application")).to_be_visible()
                customer = page.locator("#customer-form")
                customer.get_by_label("Jméno nebo firma").fill("Syntetická dílna")
                customer.get_by_label("E-mail").fill("workshop@example.invalid")
                customer.get_by_label("Telefon").fill("TEST-ONLY")
                customer.get_by_role("button", name="Uložit zákazníka").click()
                expect(page.locator("#customer-list")).to_contain_text("Syntetická dílna")
                job = page.locator("#job-form")
                job.get_by_label("Název zakázky").fill("Rekonstrukce rozvaděče · test")
                job.get_by_label("Zákazník", exact=True).select_option(label="Syntetická dílna")
                job.get_by_label("Práce (Kč)").fill("1250,50")
                job.get_by_role("button").click()
                expect(page.locator("#job-detail")).to_be_visible()
                material = page.locator("#material-form")
                material.get_by_label("Položka").fill("CYKY kabel · syntetický")
                material.get_by_label("Množství").fill("3")
                material.get_by_label("Cena za kus (Kč)").fill("109,90")
                material.get_by_role("button").click()
                expect(page.locator("#material-list")).to_contain_text("CYKY kabel")
                expect(page.locator("#detail-total")).to_contain_text("1 580,20")
                edit = page.locator("#edit-job-form")
                edit.get_by_label("Stav", exact=True).select_option("in_progress")
                edit.get_by_role("button").click()
                expect(page.locator("#job-list")).to_contain_text("V realizaci")
                page.reload(wait_until="networkidle")
                expect(page.locator("#job-list")).to_contain_text("Rekonstrukce rozvaděče")
                expect(page.locator("#identity")).to_contain_text("browser_admin")
                screenshot("app-desktop.png")
                return {"login": True, "customer_created": True, "job_created": True, "material_total_cents": 158020, "status_updated": True, "session_survives_reload": True}
            record("app-full-working-journey", app_journey)
            record("app-desktop-accessibility", lambda: audit("app-desktop"))
            def app_mobile():
                for width in (320, 390, 768, 1440):
                    page.set_viewport_size({"width": width, "height": 844})
                    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), f"App overflow at {width}px"
                page.set_viewport_size({"width": 390, "height": 844})
                screenshot("app-mobile.png")
                return {"widths_without_overflow": [320, 390, 768, 1440]}
            record("app-responsive", app_mobile)
            record("app-mobile-accessibility", lambda: audit("app-mobile"))
            def app_viewer():
                page.get_by_role("button", name="Odhlásit se").click()
                expect(page.locator("#login-view")).to_be_visible()
                login = page.locator("#login-form")
                login.get_by_label("Uživatelské jméno").fill("browser_viewer")
                login.get_by_label("Heslo", exact=True).fill(password)
                login.get_by_role("button").click()
                expect(page.locator("#job-list")).to_contain_text("Rekonstrukce rozvaděče")
                expect(page.locator("#job-form")).to_be_hidden()
                expect(page.locator("#customer-form")).to_be_hidden()
                page.get_by_role("button", name="Odhlásit se").click()
                expect(page.locator("#login-view")).to_be_visible()
                return {"read_only_ui": True, "logout": True}
            record("app-viewer-and-logout", app_viewer)
            record("no-uncaught-browser-errors", lambda: None if not errors else (_ for _ in ()).throw(AssertionError(errors)))
            if args.lighthouse_deps:
                result = run(["node", str(ROOT / "scripts/lighthouse.mjs"), str(args.lighthouse_deps.resolve()),
                              playwright.chromium.executable_path, web_url, str(out / "lighthouse.json")], ROOT,
                             approved=True, policy=Policy("trusted-local"), timeout=240)
                (out / "lighthouse.log").write_text(result["stdout"] + result["stderr"], encoding="utf-8")
                if result["status"] == "passed":
                    report["lighthouse"] = json.loads((out / "lighthouse.json").read_text())["scores"]
                else:
                    report["checks"].append({"name": "lighthouse", "status": "FAILED", "reason": "See lighthouse.log"})
            context.close()
            browser.close()
    except Exception as exc:
        report["checks"].append({"name": "browser-setup", "status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(5)
    report["status"] = "FAILED" if any(item["status"] == "FAILED" for item in report["checks"]) else "REAL VERIFIED"
    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if report["status"] == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
