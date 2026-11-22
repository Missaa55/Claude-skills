"""Two deliberately divergent, brief-specific concepts backed by dated research."""
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from builders.scaffold import ROOT, create
from distribution.installer import checked_target

FONT_POOLS = {
    "sans": [("Segoe UI", '"Segoe UI",Arial,sans-serif'), ("Trebuchet MS", '"Trebuchet MS",Arial,sans-serif'), ("Verdana", 'Verdana,"Segoe UI",sans-serif')],
    "serif": [("Georgia", 'Georgia,"Times New Roman",serif'), ("Palatino", '"Palatino Linotype",Palatino,Georgia,serif')],
}


def validate_research(data, industry, *, allow_simulated=False):
    if not isinstance(data, dict) or data.get("industry") != industry or data.get("status") != "ready":
        raise ValueError("Research must be ready and match this industry")
    if data.get("evidence_label") == "SIMULATED" and not allow_simulated:
        raise ValueError("Simulated research is only for explicitly labelled tests")
    observed = datetime.fromisoformat(data["observed_at"])
    if observed.tzinfo is None:
        raise ValueError("Research needs a timezone")
    age = (datetime.now(timezone.utc) - observed).total_seconds()
    if not -300 <= age <= 7 * 86400:
        raise ValueError("Refresh research: older than 7 days or future timestamp")
    accepted_labels = {"REAL VERIFIED", "SIMULATED"} if allow_simulated and data.get("evidence_label") == "SIMULATED" else {"REAL VERIFIED"}
    accepted = [v for v in data.get("candidates", []) if v.get("fetch_status") in accepted_labels]
    if any(not isinstance(v.get("final_url"), str) or urlsplit(v["final_url"]).scheme != "https" or not urlsplit(v["final_url"]).hostname for v in accepted):
        raise ValueError("Invalid research source URL")
    domains = {urlsplit(v["final_url"]).hostname.removeprefix("www.") for v in accepted}
    if len(domains) < 20 or any(not v.get("source_sha256") or not isinstance(v.get("signals"), dict) for v in accepted):
        raise ValueError("At least 20 distinct successfully inspected sites are required")
    if data.get("analyzed") != len(domains):
        raise ValueError("Research source count does not match its records")
    for item in accepted:
        signals = item["signals"]
        if not isinstance(signals.get("font_classes"), list) or any(v not in ("sans", "serif") for v in signals["font_classes"]):
            raise ValueError("Invalid font observations")
        if any(type(signals.get(key)) is not bool for key in ("grid", "sticky", "motion")):
            raise ValueError("Invalid structural observations")
    return accepted


def directions(task, name, industry, research, scroll="auto"):
    if industry not in ("electrical", "footwear") or scroll not in ("auto", "off", "story"):
        raise ValueError("Unsupported industry or scrolling policy")
    if not isinstance(task, str) or not 5 <= len(task.strip()) <= 6000 or not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
        raise ValueError("Supply a meaningful task and brand name")
    seed = int(hashlib.sha256((name + task + industry).encode()).hexdigest()[:8], 16)
    aggregate = research.get("aggregate", {})
    current_class = "serif" if aggregate.get("serif", 0) > aggregate.get("sans", 0) else "sans"
    grid_observed = aggregate.get("grid", 0) * 2 >= research.get("analyzed", 20)
    original_class = "sans" if current_class == "serif" else "serif"
    font_a = FONT_POOLS[current_class][seed % len(FONT_POOLS[current_class])]
    font_b = FONT_POOLS[original_class][(seed // 3) % len(FONT_POOLS[original_class])]
    story_fits = industry == "footwear" or bool(re.search(r"příběh|pribeh|story|portfolio|proces|postup", task, re.I))
    story = scroll == "story" or scroll == "auto" and story_fits
    a = {"id": "a", "name": "Oborově srozumitelný", "font_class": current_class, "heading_font": font_a[0],
         "font_stack": font_a[1], "palette": "navy-amber" if industry == "electrical" else "graphite-coral",
         "hero_layout": "split", "composition": "three-column" if grid_observed else "stacked-services", "surfaces": "technical-panels",
         "graphic_language": "schematic" if industry == "electrical" else "product-grid", "scroll": "native",
         "rationale": f"Font class follows the sampled HTML/CSS signals ({aggregate.get(current_class, 0)} sites); other choices prioritize sector clarity, not cloning a competitor."}
    b = {"id": "b", "name": "Autorský kontrast", "font_class": original_class, "heading_font": font_b[0],
         "font_stack": font_b[1], "palette": "indigo-lime" if industry == "electrical" else "plum-mint",
         "hero_layout": "editorial-stack", "composition": "horizontal-editorial", "surfaces": "open-canvas",
         "graphic_language": "continuous-circuit" if industry == "electrical" else "oversized-editorial",
         "scroll": "sticky-story" if story else "native",
         "rationale": "Deliberately changes typography, palette, composition and visual metaphor. Native scrolling remains under the visitor's control."}
    dimensions = ("font_class", "palette", "hero_layout", "composition", "surfaces", "graphic_language", "scroll")
    differences = [{"dimension": key, "a": a[key], "b": b[key], "different": a[key] != b[key]} for key in dimensions]
    score = sum(v["different"] for v in differences)
    if score < 5:
        raise ValueError("Concepts are not sufficiently different")
    return {"task": task, "industry": industry, "brand": name, "concepts": [a, b],
            "differences": differences, "distinct_dimensions": score, "total_dimensions": len(dimensions),
            "forecast": {"evidence_label": "NOT VERIFIED", "horizon_years": 3,
                         "reason": "Longevity is a design intent, not a prediction of future taste",
                         "principles": ["Readable type", "Accessible contrast", "Progressive enhancement", "No scroll hijacking", "Reduced-motion support", "Small dependency-free output"]},
            "scroll_decision": "Story helps this brief" if story else "Direct service navigation is more useful for this brief",
            "font_note": "Individually selected system stacks; no unlicensed font files or third-party font tracking"}


def _refresh_manifest(project, concept):
    path = project / "builder-manifest.json"
    manifest = json.loads(path.read_text())
    manifest["design"] = concept
    manifest["files"] = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted(project.rglob("*")) if p.is_file() and p.name != "builder-manifest.json"}
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def design(task, name, industry, research, workspace, *, scroll="auto", allow_simulated=False):
    accepted = validate_research(research, industry, allow_simulated=allow_simulated)
    aggregate = {key: sum(key in v["signals"]["font_classes"] for v in accepted) for key in ("sans", "serif")}
    aggregate.update({key: sum(v["signals"][key] for v in accepted) for key in ("grid", "sticky", "motion")})
    research = {**research, "aggregate": aggregate}
    plan = directions(task, name, industry, research, scroll)
    workspace = checked_target(workspace)
    workspace.mkdir(parents=True, exist_ok=False)
    for concept in plan["concepts"]:
        project = workspace / concept["id"]
        create({"builder": "web", "task": task, "name": name, "region": "Brno a okolí" if industry == "electrical" else "Ukázková kolekce"}, project)
        if industry == "footwear":
            source = ROOT / "builders/templates/footwear"
            content = (source / "index.html").read_text(encoding="utf-8").replace("@@NAME@@", html.escape(name, quote=True))
            (project / "index.html").write_text(content, encoding="utf-8")
            (project / "catalog.js").write_bytes((source / "catalog.js").read_bytes())
            (project / "mark.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40"><rect width="40" height="40" rx="4" fill="#202a33"/><path d="M12 9V31M28 9 13 21 29 31" fill="none" stroke="#ffc2a5" stroke-width="3"/></svg>', encoding="utf-8")
            with (project / "style.css").open("a", encoding="utf-8") as stream:
                stream.write((source / "style.css").read_text(encoding="utf-8"))
            for rel in ("server.py", "tests/test_http.py"):
                path = project / rel
                value = path.read_text(encoding="utf-8")
                for before, after in (("Rekonstrukce elektroinstalace", "Výběr obuvi"), ("Nová elektroinstalace", "Velikost a střih"), ("Revize a měření", "Péče o obuv"), ("Chytrá domácnost", "Jiný dotaz")):
                    value = value.replace(before, after)
                if rel == "server.py": value = value.replace('"/mark.svg",', '"/mark.svg", "/catalog.js",')
                path.write_text(value, encoding="utf-8")
            path = project / "build.py"
            path.write_text(path.read_text().replace('"mark.svg")', '"mark.svg", "catalog.js")'), encoding="utf-8")
        css = f"\n/* Brief-specific design: {concept['id']} */\nh1,h2,h3{{font-family:{concept['font_stack']}}}\n"
        if concept["id"] == "a" and concept["composition"] == "stacked-services":
            css += ".services{display:block}.services article{padding-block:28px}.services h3{max-width:none;min-height:0}.services .service-icon{float:right}.services ul{display:flex;flex-wrap:wrap;gap:10px 34px}\n"
        if concept["id"] == "b":
            ink, accent, wash = ("#242252", "#d3ef54", "#eef1ff") if industry == "electrical" else ("#49243f", "#b6e7cc", "#f6f0f5")
            css += f":root{{--ink:{ink};--accent:{accent};--wash:{wash}}}\n"
            css += ".hero{display:flex;flex-direction:column;align-items:stretch;gap:40px;padding-top:70px}.hero-copy{max-width:100%}.hero h1{font-size:clamp(3rem,6.5vw,6.7rem);font-weight:500;max-width:1100px}.hero .intro{max-width:650px;font-size:1.25rem}.hero em{background:none;font-style:italic;color:var(--ink)}.technical-panel{width:75%;align-self:flex-end;box-shadow:none;transform:none;border-radius:70px 0 70px 0}.services{display:block}.services article{display:grid;grid-template-columns:1fr 1.4fr 1fr;gap:34px;padding:30px 0}.services .service-icon{display:none}.services h3{font-size:1.7rem}.services ul{border:0;padding-top:0;margin-top:0}.projects{display:block}.project{display:grid;grid-template-columns:1.25fr 1fr;gap:0 40px;margin-bottom:38px}.project-art{grid-row:1/4;margin-bottom:0}.project>.eyebrow{align-self:end}.project>p:last-child{align-self:start}.button{border-radius:28px}.brand img{border-radius:50%}.principles{border-color:var(--ink)}.references{background:var(--wash)}\n"
            if industry == "footwear":
                css += ".product-scene{min-height:480px;background:#e9dfea;border-radius:90px 0 0 0}.hero-shoe{max-width:850px;transform:rotate(-13deg)}.product-grid{display:block}.product-card{display:grid;grid-template-columns:1.3fr 1fr;gap:0 40px;margin-bottom:50px;align-items:center}.shoe-visual{grid-row:1/5;margin:0}.product-card>h3{font-size:2.5rem}.services article{grid-template-columns:1fr 2fr}@media(max-width:760px){.product-scene{min-height:320px;border-radius:35px 0 0 0}.product-card{display:block}.shoe-visual{margin-bottom:22px}.product-card>h3{font-size:2rem}}\n"
            if industry == "electrical":
                page = (project / "index.html").read_text(encoding="utf-8")
                graph = '<svg class="plan" viewBox="0 0 600 230" role="img" aria-label="Autorská kresba propojených elektrických okruhů"><g fill="none" stroke="#d3ef54" stroke-width="3"><path d="M35 115H565M140 115V50H300V180H470V115M140 115V180H210M390 115V50H470"/><circle cx="140" cy="115" r="30"/><circle cx="300" cy="115" r="70"/><circle cx="470" cy="115" r="30"/></g><g fill="#ffffff"><circle cx="35" cy="115" r="7"/><circle cx="565" cy="115" r="7"/></g></svg>'
                page = re.sub(r'<svg class="plan".*?</svg>', graph, page, count=1, flags=re.S)
                (project / "index.html").write_text(page, encoding="utf-8")
            if concept["scroll"] == "sticky-story":
                css += "@media(min-width:900px){#postup{display:grid;grid-template-columns:1fr 1fr;gap:30px}#postup>.eyebrow{grid-column:1/-1}#postup>h2{position:sticky;top:5rem;align-self:start}#postup>.steps{display:block;margin:0}#postup .steps li{min-height:32vh;padding-top:30px}#postup .steps li.is-current{border-top:3px solid var(--ink)}}\n"
                with (project / "site.js").open("a", encoding="utf-8") as stream:
                    stream.write("\nif(!matchMedia('(prefers-reduced-motion: reduce)').matches){const storyObserver=new IntersectionObserver(entries=>entries.forEach(entry=>entry.target.classList.toggle('is-current',entry.isIntersecting)),{rootMargin:'-20% 0px -30% 0px'});document.querySelectorAll('#postup .steps li').forEach(step=>storyObserver.observe(step));}\n")
            css += "@media(max-width:760px){.hero{padding-top:35px}.hero h1{font-size:3.05rem}.hero .intro{font-size:1rem}.technical-panel{width:100%;border-radius:25px 0 25px 0}.services article{display:block}.project{display:block}.project-art{margin-bottom:20px}.project>.eyebrow{margin-top:22px}.services h3{font-size:1.6rem}}@media(prefers-reduced-motion:reduce){#postup>h2{position:static!important}}\n"
        elif industry == "footwear":
            css += ":root{--ink:#202a33;--accent:#ffc2a5;--wash:#f1f5f7}\n"
        with (project / "style.css").open("a", encoding="utf-8") as stream:
            stream.write(css)
        _refresh_manifest(project, concept)
    plan.update({"research_observed_at": research["observed_at"], "analyzed_candidates": research["analyzed"],
                 "evidence_label": "SIMULATED" if research.get("evidence_label") == "SIMULATED" else "STATIC CHECK",
                 "generation": "deterministic-reference", "ai_generation": "NOT VERIFIED",
                 "validation": "NOT VERIFIED", "workspace": str(workspace)})
    (workspace / "design-comparison.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return plan
