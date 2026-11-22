"""Bounded public-HTTPS research. Downloads HTML/CSS only; never executes a site."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import http.client
import ipaddress
import json
import re
import socket
import ssl
import sys
from urllib.parse import urljoin, urlsplit

MIN_CANDIDATES = 20
MAX_BODY = 1_000_000


def public_target(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Only public HTTPS without credentials on port 443 is allowed")
    if parsed.fragment or re.search(r"(?i)(token|key|password|secret|auth)=", parsed.query):
        raise ValueError("Credential-like query parameters and fragments are not collected")
    host = parsed.hostname.encode("idna").decode("ascii")
    if host.endswith((".localhost", ".local", ".internal")) or host == "localhost":
        raise ValueError("Private host rejected")
    answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    addresses = list(dict.fromkeys(answer[4][0] for answer in answers))
    if not addresses or any(not ipaddress.ip_address(address).is_global or ipaddress.ip_address(address).is_multicast for address in addresses):
        raise ValueError("Private, reserved or mixed DNS answers rejected")
    return parsed, host, addresses[0]


def fetch(url, redirects=0):
    parsed, host, address = public_target(url)
    if redirects > 3:
        raise ValueError("Redirect limit reached")
    context = ssl.create_default_context()
    connection = http.client.HTTPSConnection(host, timeout=8, context=context)
    # Pin the validated IP for this connection while preserving TLS SNI/verification.
    connection.sock = context.wrap_socket(socket.create_connection((address, 443), timeout=8), server_hostname=host)
    try:
        connection.request("GET", (parsed.path or "/") + (("?" + parsed.query) if parsed.query else ""),
                           headers={"User-Agent": "ClaudeSkills-DesignResearch/0.2 (public metadata only)", "Accept": "text/html,text/css", "Connection": "close"})
        response = connection.getresponse()
        if response.status in (301, 302, 303, 307, 308):
            destination = urljoin(url, response.getheader("Location", ""))
            return fetch(destination, redirects + 1)
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}")
        kind = response.getheader("Content-Type", "").lower()
        if not kind.startswith(("text/html", "text/css", "application/xhtml+xml")):
            raise ValueError("Non-HTML/CSS response rejected")
        data = response.read(MAX_BODY + 1)
        if len(data) > MAX_BODY:
            raise ValueError("Response exceeds byte limit")
        return url, data.decode("utf-8", "replace"), hashlib.sha256(data).hexdigest()
    finally:
        connection.close()


class Signals(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title, self.title, self.css, self.counts = False, "", [], Counter()
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.counts[tag] += 1
        if tag == "title": self.in_title = True
        if tag == "link" and "stylesheet" in attrs.get("rel", "") and attrs.get("href"):
            self.css.append(attrs["href"])
    def handle_endtag(self, tag):
        if tag == "title": self.in_title = False
    def handle_data(self, data):
        if self.in_title: self.title += data


def observe(url):
    try:
        final_url, content, digest = fetch(url)
        parser = Signals()
        parser.feed(content)
        css, stylesheets = content, []
        for value in parser.css[:2]:
            style_url = urljoin(final_url, value)
            # Avoid fetching arbitrary third-party trackers, scripts or font binaries.
            if urlsplit(style_url).hostname != urlsplit(final_url).hostname:
                continue
            try:
                location, style, sha = fetch(style_url)
                css += "\n" + style
                stylesheets.append({"url": location, "sha256": sha})
            except (OSError, ValueError, http.client.HTTPException):
                continue
        fonts = re.findall(r"font-family\s*:\s*([^;}]+)", css, re.I)
        classes = []
        joined = " ".join(fonts).lower()
        if re.search(r"sans|arial|roboto|inter\b|montserrat|open sans", joined): classes.append("sans")
        if re.search(r"georgia|times|palatino|(?<!sans-)\bserif", joined): classes.append("serif")
        colors = Counter(value.lower() for value in re.findall(r"#[0-9a-fA-F]{6}\b", css))
        return {"url": url, "final_url": final_url, "fetch_status": "REAL VERIFIED", "analysis": "STATIC CHECK",
                "visual_review": "NOT VERIFIED", "title": " ".join(parser.title.split()[:20]), "source_sha256": digest,
                "stylesheets": stylesheets, "signals": {"font_classes": classes, "colors": dict(colors.most_common(6)),
                  "grid": bool(re.search(r"display\s*:\s*grid", css)), "sticky": bool(re.search(r"position\s*:\s*sticky", css)),
                  "motion": bool(re.search(r"@keyframes|scroll-timeline|animation\s*:", css)),
                  "image_count": parser.counts["img"], "form_count": parser.counts["form"]}}
    except (OSError, ValueError, http.client.HTTPException) as exc:
        return {"url": url, "fetch_status": "FAILED", "reason": str(exc), "visual_review": "NOT VERIFIED"}


def collect(candidates: dict) -> dict:
    urls = candidates.get("urls") if isinstance(candidates, dict) else None
    industry = candidates.get("industry") if isinstance(candidates, dict) else None
    if industry not in ("electrical", "footwear") or not isinstance(urls, list) or not 20 <= len(urls) <= 40 or any(not isinstance(u, str) or len(u) > 2000 for u in urls):
        raise ValueError("Supply an industry and 20–40 candidate URLs")
    hosts = [urlsplit(url).hostname for url in urls]
    if None in hosts or len(set(host.removeprefix("www.") for host in hosts)) != len(hosts):
        raise ValueError("Candidates must have distinct domains")
    with ThreadPoolExecutor(max_workers=4) as pool:
        observations = list(pool.map(observe_bounded, urls))
    seen, accepted = set(), []
    for observation in observations:
        if observation["fetch_status"] == "REAL VERIFIED":
            host = urlsplit(observation["final_url"]).hostname.removeprefix("www.")
            if host not in seen:
                accepted.append(observation)
                seen.add(host)
    aggregate = Counter()
    for item in accepted:
        signals = item["signals"]
        for font in signals["font_classes"]:
            aggregate[font] += 1
        for feature in ("grid", "sticky", "motion"):
            aggregate[feature] += int(signals[feature])
    return {"schema_version": 1, "industry": industry, "observed_at": datetime.now(timezone.utc).isoformat(),
            "status": "ready" if len(accepted) >= MIN_CANDIDATES else "insufficient_evidence",
            "evidence_label": "STATIC CHECK", "attempted": len(urls), "analyzed": len(accepted),
            "aggregate": dict(aggregate), "candidates": observations,
            "longitudinal_trend": "NOT VERIFIED; a single snapshot does not establish change over time",
            "limitations": ["Convenience sample, not representative market/popularity statistics",
                            "HTML/CSS signals are not computed visual designs; no remote JS was executed",
                            "No future trend is established and no third-party copy, images or CSS are reused"]}


def observe_bounded(url):
    # A separate process enforces a total deadline even for slow DNS/header/body
    # trickles. Only our HTML/CSS parser executes; no downloaded JS executes.
    from pathlib import Path
    from core.process import Policy, run
    script = Path(__file__).resolve()
    result = run([sys.executable, str(script), "--observe", url], script.parents[1],
                 approved=True, policy=Policy("trusted-local"), timeout=30, max_output=64000)
    if result["status"] != "passed":
        return {"url": url, "fetch_status": "FAILED", "reason": "Bounded fetch: " + result["status"], "visual_review": "NOT VERIFIED"}
    try:
        return json.loads(result["stdout"])
    except ValueError:
        return {"url": url, "fetch_status": "FAILED", "reason": "Invalid parser response", "visual_review": "NOT VERIFIED"}


def compare_samples(current, previous):
    if current.get("industry") != previous.get("industry"):
        raise ValueError("Trend comparison requires the same industry")
    start, end = (datetime.fromisoformat(report["observed_at"]) for report in (previous, current))
    if start.tzinfo is None or end.tzinfo is None or (end - start).total_seconds() < 86400:
        raise ValueError("Trend snapshots must be at least a day apart")
    def index(report):
        return {urlsplit(v["final_url"]).hostname.removeprefix("www."): v["signals"] for v in report["candidates"] if v["fetch_status"] == "REAL VERIFIED"}
    before, after = index(previous), index(current)
    common = set(before) & set(after)
    if len(common) < 20:
        raise ValueError("Trend comparison requires at least 20 matching domains")
    changes = {}
    for key in ("grid", "sticky", "motion"):
        old, new = sum(bool(before[d][key]) for d in common), sum(bool(after[d][key]) for d in common)
        changes[key] = {"before": old, "after": new, "percentage_points": round((new-old) / len(common) * 100, 1)}
    return {"evidence_label": "STATIC CHECK", "matched_sites": len(common), "changes": changes,
            "notice": "Change in this HTML/CSS sample only; market popularity and future direction remain NOT VERIFIED"}


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--observe":
        raise SystemExit("Internal bounded observer: --observe HTTPS_URL")
    print(json.dumps(observe(sys.argv[2]), ensure_ascii=False))
