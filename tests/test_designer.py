from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from builders.designer import design, directions, validate_research
from builders.research import public_target, compare_samples


def synthetic_research(industry="electrical"):
    return {"schema_version": 1, "status": "ready", "evidence_label": "SIMULATED", "industry": industry,
            "observed_at": datetime.now(timezone.utc).isoformat(), "analyzed": 20,
            "aggregate": {"sans": 20}, "candidates": [{"final_url": f"https://site{i}.example.com/", "fetch_status": "SIMULATED", "source_sha256": "0"*64,
             "signals": {"font_classes": ["sans"], "grid": True, "sticky": False, "motion": False}} for i in range(20)]}


class DesignerTests(unittest.TestCase):
    def test_minimum_twenty_fresh_distinct_sources(self):
        data = synthetic_research()
        with self.assertRaises(ValueError):
            validate_research(data, "electrical")
        self.assertEqual(len(validate_research(data, "electrical", allow_simulated=True)), 20)
        data["candidates"].pop()
        with self.assertRaises(ValueError):
            validate_research(data, "electrical", allow_simulated=True)
        data = synthetic_research()
        data["observed_at"] = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        with self.assertRaises(ValueError):
            validate_research(data, "electrical", allow_simulated=True)

    def test_two_concepts_change_structure_and_fonts(self):
        plan = directions("Elektroinstalace a přehledný postup zakázky", "Syntetická značka", "electrical", synthetic_research())
        self.assertGreaterEqual(plan["distinct_dimensions"], 5)
        self.assertNotEqual(plan["concepts"][0]["font_stack"], plan["concepts"][1]["font_stack"])
        self.assertEqual(plan["concepts"][1]["scroll"], "sticky-story")
        self.assertEqual(plan["forecast"]["evidence_label"], "NOT VERIFIED")

    def test_native_scrolling_for_direct_service(self):
        plan = directions("Rychlá poptávka elektrikáře", "Synthetic", "electrical", synthetic_research(), "auto")
        self.assertEqual(plan["concepts"][1]["scroll"], "native")

    def test_generates_both_industries_without_copying_source_sites(self):
        with tempfile.TemporaryDirectory() as temp:
            for industry in ("electrical", "footwear"):
                root = Path(temp) / industry
                result = design("Vytvoř přístupný návrh s příběhem", "Synthetic Design", industry, synthetic_research(industry), root, allow_simulated=True)
                self.assertEqual(result["evidence_label"], "SIMULATED")
                a = (root / "a/index.html").read_text(encoding="utf-8")
                b = (root / "b/style.css").read_text(encoding="utf-8")
                self.assertIn("Synthetic Design", a)
                self.assertIn("position:sticky", b)
                self.assertNotIn("site0.example.com", a)
                if industry == "footwear":
                    self.assertNotIn("rozvaděč", a)
                    self.assertTrue((root / "a/catalog.js").is_file())

    @patch("builders.research.socket.getaddrinfo")
    def test_ssrf_rejects_private_mixed_and_multicast_dns(self, dns):
        for answers in (("127.0.0.1",), ("93.184.216.34", "10.0.0.1"), ("224.0.0.1",)):
            dns.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443)) for address in answers]
            with self.assertRaises(ValueError):
                public_target("https://example.com/")
        for url in ("file:///etc/passwd", "http://example.com", "https://user:password@example.com", "https://example.com:8080", "https://example.com/?token=synthetic"):
            with self.assertRaises(ValueError):
                public_target(url)

    def test_longitudinal_claim_needs_comparable_snapshots(self):
        before, after = synthetic_research(), synthetic_research()
        for report in (before, after):
            for row in report["candidates"]:
                row["fetch_status"] = "REAL VERIFIED"  # Mock transport results, not actual sites.
        with self.assertRaises(ValueError):
            compare_samples(after, before)
        before["observed_at"] = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        after["candidates"][0]["signals"]["sticky"] = True
        result = compare_samples(after, before)
        self.assertEqual(result["changes"]["sticky"]["percentage_points"], 5)


if __name__ == "__main__":
    unittest.main()
