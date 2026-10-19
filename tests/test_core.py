import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from revprobe.core import anchors, build_suite, digest, evaluate_suite, paragraphs


OLD = "# Support policy\n\n## Refund window\n\nCustomers can request a refund within 30 days of purchase.\n\n## Contact\n\nEmail support@example.com.\n"
NEW = "# Support policy\n\n## Refund window\n\nCustomers can request a refund within 14 days of purchase.\n\n## Contact\n\nEmail support@example.com.\n"


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.suite = build_suite(OLD, NEW, "policy.md")
        self.case = self.suite["cases"][0]

    def test_paragraph_headings(self):
        self.assertEqual(paragraphs(OLD)[0]["heading"], "Refund window")

    def test_generates_only_changed_section(self):
        self.assertEqual(len(self.suite["cases"]), 1)
        self.assertEqual(self.case["section"], "Refund window")
        self.assertEqual((self.case["old_anchor"], self.case["new_anchor"]), ("30", "14"))
        self.assertEqual(self.suite["new_sha256"], digest(NEW))

    def test_stable_case_id(self):
        self.assertEqual(self.case["id"], build_suite(OLD, NEW, "policy.md")["cases"][0]["id"])

    def test_unchanged_doc_has_no_cases(self):
        self.assertEqual(build_suite(NEW, NEW, "policy.md")["cases"], [])

    def test_no_checkable_anchor_is_skipped(self):
        self.assertIsNone(anchors("abc", "abc"))

    def test_fresh_answer_passes(self):
        report = evaluate_suite(self.suite, {self.case["id"]: {"answer": "The limit is 14 days.", "source_sha256": digest(NEW)}})
        self.assertEqual(report["summary"], {"pass": 1, "fail": 0, "inconclusive": 0})

    def test_stale_answer_fails(self):
        report = evaluate_suite(self.suite, {self.case["id"]: {"answer": "The limit is 30 days."}})
        self.assertEqual(report["results"][0]["reason"], "old_anchor_in_answer")

    def test_stale_revision_fails_even_if_answer_looks_fresh(self):
        report = evaluate_suite(self.suite, {self.case["id"]: {"answer": "14 days", "source_sha256": digest(OLD)}})
        self.assertEqual(report["results"][0]["reason"], "stale_source_revision")

    def test_missing_and_ambiguous_are_inconclusive(self):
        self.assertEqual(evaluate_suite(self.suite, {})["summary"]["inconclusive"], 1)
        report = evaluate_suite(self.suite, {self.case["id"]: {"answer": "Previously 30, now 14 days."}})
        self.assertEqual(report["results"][0]["reason"], "both_anchors_in_answer")

    def test_anchor_matches_whole_number(self):
        report = evaluate_suite(self.suite, {self.case["id"]: {"answer": "The code is 214."}})
        self.assertEqual(report["results"][0]["reason"], "no_anchor_in_answer")


if __name__ == "__main__":
    unittest.main()
