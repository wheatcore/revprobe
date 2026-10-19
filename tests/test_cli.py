import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import io

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from revprobe.cli import main, target_response


class FakeReply(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class CliTests(unittest.TestCase):
    def test_generate_and_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old, new = root / "old.md", root / "new.md"
            suite, answers, report, markdown = (root / name for name in ("suite.json", "answers.json", "report.json", "report.md"))
            old.write_text("## Limit\n\nRetention is 90 days.\n", encoding="utf-8")
            new.write_text("## Limit\n\nRetention is 60 days.\n", encoding="utf-8")
            self.assertEqual(main(["generate", "--old", str(old), "--new", str(new), "--output", str(suite)]), 0)
            data = json.loads(suite.read_text(encoding="utf-8"))
            answers.write_text(json.dumps({data["cases"][0]["id"]: {"answer": "Retention is 60 days."}}), encoding="utf-8")
            self.assertEqual(main(["run", "--suite", str(suite), "--responses", str(answers), "--output", str(report), "--markdown", str(markdown)]), 0)
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["summary"]["pass"], 1)
            self.assertIn("PASS", markdown.read_text(encoding="utf-8"))

    def test_inconclusive_exit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            suite = {"schema_version": 1, "source": "x", "new_sha256": "hash", "cases": [{"id": "1", "section": "s", "question": "q", "old_anchor": "30", "new_anchor": "14"}]}
            (root / "suite.json").write_text(json.dumps(suite), encoding="utf-8")
            (root / "answers.json").write_text("{}", encoding="utf-8")
            self.assertEqual(main(["run", "--suite", str(root / "suite.json"), "--responses", str(root / "answers.json"), "--output", str(root / "report.json")]), 1)

    def test_live_target_contract(self):
        with patch("revprobe.cli.urlopen", return_value=FakeReply(b'{"answer":"14 days"}')) as mocked:
            response = target_response("http://localhost:8000/answer", {"id": "abc", "question": "Current window?"}, 3)
        self.assertEqual(response["answer"], "14 days")
        request = mocked.call_args.args[0]
        self.assertEqual(json.loads(request.data), {"query": "Current window?", "case_id": "abc"})


if __name__ == "__main__":
    unittest.main()
