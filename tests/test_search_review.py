"""Behavior checks for the review's main business and input risks.

Run with: python -m unittest discover -s tests -v
Fixtures are temporary workbooks; no ad accounts or external services are used.
"""

import contextlib
import csv
import io
import json
import sys
import tempfile
import unittest
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import search_review as review


class SearchReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.config = review.read_config(ROOT / "config.json")

    def workbook(self, rows, product="Voice AI Agents", source_date="2026-10-01", headers=None):
        path = self.folder / "input.xlsx"
        book = Workbook()
        sheet = book.active
        sheet.title = self.config["search_sheet"]
        sheet.append(headers or review.REQUIRED)
        for row in rows:
            sheet.append(row)
        if product is not None:
            campaigns = book.create_sheet(self.config["campaign_sheet"])
            campaigns.append(["Campaign", "Product"])
            campaigns.append(["Test Campaign", product])
        if source_date is not None:
            readme = book.create_sheet("README")
            readme.append([f"Data pulled {source_date}."])
        book.save(path)
        book.close()
        return path

    def record(self, term="voice ai jobs", cost=700, clicks=70, leads=0, match="Broad"):
        return [term, "Test Campaign", match, 1000, clicks, cost, 4, leads]

    def report(self, path, as_of=date(2026, 10, 1)):
        rows, pulled, warnings, count = review.read_dataset(path, self.config)
        return review.build_report(rows, self.config, pulled, as_of, path, warnings, count)

    def test_changed_numbers_change_the_recommendation(self):
        low = self.report(self.workbook([self.record(cost=499)]))
        self.assertEqual(low["results"][0]["action"], "MONITOR")
        high = self.report(self.workbook([self.record(cost=500, clicks=50)]))
        self.assertEqual(high["results"][0]["action"], "PROPOSE_EXACT_NEGATIVE")
        lead = self.report(self.workbook([self.record(cost=500, clicks=50, leads=1)]))
        self.assertEqual(lead["results"][0]["action"], "KEEP")

    def test_buyer_language_is_not_excluded_for_zero_leads(self):
        terms = ["voice ai pricing", "vapi alternative", "retell ai vs", "voice generator api", "enterprise voice generator platform", "customer support ai platform"]
        report = self.report(self.workbook([self.record(term=t) for t in terms]))
        self.assertTrue(all(r["action"] == "REVIEW" for r in report["results"]))

    def test_free_developer_query_remains_ambiguous(self):
        report = self.report(self.workbook([self.record(term="free llm api")], product="Inference API (new)"))
        self.assertEqual(report["results"][0]["action"], "REVIEW")
        self.assertEqual(report["results"][0]["proposed_negative"], "")

    def test_unknown_product_cannot_propose_a_negative(self):
        report = self.report(self.workbook([self.record()], product=None))
        self.assertEqual(report["results"][0]["action"], "REVIEW")
        self.assertTrue(report["warnings"])

    def test_blank_leads_fail_instead_of_becoming_zero(self):
        with self.assertRaises(review.InputError):
            self.report(self.workbook([self.record(leads=None)]))

    def test_invalid_numeric_values_fail(self):
        for cost in (-1, "NaN", "not a cost"):
            with self.subTest(cost=cost), self.assertRaises(review.InputError):
                self.report(self.workbook([self.record(cost=cost)]))

    def test_missing_column_and_empty_exports_fail(self):
        with self.assertRaises(review.InputError):
            self.report(self.workbook([], headers=review.REQUIRED[:-1]))
        with self.assertRaises(review.InputError):
            self.report(self.workbook([]))

    def test_duplicate_match_type_rows_are_rejected(self):
        with self.assertRaises(review.InputError):
            self.report(self.workbook([self.record(), self.record(term="  VOICE  AI JOBS  ")]))

    def test_match_types_aggregate_before_deciding(self):
        path = self.workbook([self.record(cost=300, clicks=30), self.record(cost=300, clicks=30, match="Exact", leads=1)])
        report = self.report(path)
        self.assertEqual(len(report["results"]), 1)
        row = report["results"][0]
        self.assertEqual(row["source_rows"], [2, 3])
        self.assertEqual(row["cost"], 600)
        self.assertEqual(row["action"], "KEEP")

    def test_stale_and_undated_exports_need_refresh(self):
        path = self.workbook([self.record()])
        report = self.report(path, as_of=date(2026, 11, 13))
        self.assertEqual(report["source"]["age_days"], 43)
        self.assertEqual(report["source"]["freshness"], "stale")
        self.assertEqual(report["results"][0]["freshness_gate"], "REFRESH_REQUIRED")
        unknown = self.report(self.workbook([self.record()], source_date=None))
        self.assertEqual(unknown["source"]["freshness"], "unknown")
        self.assertEqual(unknown["results"][0]["freshness_gate"], "REFRESH_REQUIRED")

    def test_future_source_date_fails(self):
        with self.assertRaises(review.InputError):
            self.report(self.workbook([self.record()], source_date="2026-10-02"))

    def test_report_does_not_approve_or_apply_changes(self):
        report = self.report(self.workbook([self.record()]))
        row = report["results"][0]
        self.assertEqual(row["approval_status"], "AWAITING_HUMAN_REVIEW")
        self.assertEqual(row["negative_match_type"], "Exact")
        self.assertEqual(row["change_scope"], "Campaign only")
        self.assertEqual(report["automation_boundary"]["platform_changes_applied"], 0)
        self.assertIn("not projected savings", review.summary_markdown(report))

    def test_outputs_preserve_evidence_and_escape_spreadsheet_and_html_content(self):
        term = '+HYPERLINK("https://example.invalid") </script><script>alert(1)</script>'
        report = self.report(self.workbook([self.record(term=term)]))
        output = self.folder / "results"
        review.write_outputs(report, output)
        self.assertEqual({p.name for p in output.iterdir()}, {"summary.md", "report.json", "report.html", "proposals.csv"})
        raw = json.loads((output / "report.json").read_text())
        self.assertEqual(raw["results"][0]["search_term"], term)
        with (output / "proposals.csv").open(encoding="utf-8-sig", newline="") as handle:
            self.assertTrue(next(csv.DictReader(handle))["search_term"].startswith("'+"))
        markup = (output / "report.html").read_text()
        self.assertNotIn("<script>alert(1)</script>", markup)
        self.assertIn("&lt;script&gt;", markup)
        class ScriptParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.scripts = 0
                self.in_payload = False
                self.payload = ""

            def handle_starttag(self, tag, attrs):
                if tag == "script":
                    self.scripts += 1
                    self.in_payload = dict(attrs).get("id") == "review-data"

            def handle_endtag(self, tag):
                if tag == "script":
                    self.in_payload = False

            def handle_data(self, data):
                if self.in_payload:
                    self.payload += data

        parser = ScriptParser()
        parser.feed(markup)
        self.assertEqual(parser.scripts, 2, "Dataset text must not create a third script element.")
        self.assertEqual(json.loads(parser.payload)["rows"][0]["search_term"], term)

    def test_invalid_input_returns_nonzero_and_no_new_report(self):
        path = self.workbook([self.record(leads=None)])
        output = self.folder / "bad_output"
        with contextlib.redirect_stderr(io.StringIO()):
            status = review.main(["--input", str(path), "--output", str(output)])
        self.assertEqual(status, 2)
        self.assertFalse(output.exists())

    def test_config_numeric_strings_are_normalized_or_clearly_rejected(self):
        config = dict(self.config, min_spend="500", min_clicks="50")
        path = self.folder / "config.json"
        path.write_text(json.dumps(config))
        try:
            parsed = review.read_config(path)
        except review.InputError:
            return
        row = {"search_term": "voice ai jobs", "cost": 600, "clicks": 60, "crm_leads": 0, "product": "voice"}
        self.assertEqual(review.classify(row, parsed)[0], "PROPOSE_EXACT_NEGATIVE")


if __name__ == "__main__":
    unittest.main()
