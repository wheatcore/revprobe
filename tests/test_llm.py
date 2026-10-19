import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from revprobe.llm import improve_question


class FakeReply(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class LlmTests(unittest.TestCase):
    def test_model_question_and_request_shape(self):
        case = {"section": "Refunds", "old_text": "30 days", "new_text": "14 days", "old_anchor": "30", "new_anchor": "14"}
        body = {"choices": [{"message": {"content": '{"question":"What is the current refund window?"}'}}]}
        with patch("revprobe.llm.urlopen", return_value=FakeReply(json.dumps(body).encode())) as mocked:
            question = improve_question(case, model="local", api_base="http://localhost:11434/v1", api_key="test")
        self.assertEqual(question, "What is the current refund window?")
        request = mocked.call_args.args[0]
        self.assertEqual(request.full_url, "http://localhost:11434/v1/chat/completions")
        self.assertIn("OLD: 30 days", request.data.decode())

    def test_rejects_question_that_contains_answer(self):
        case = {"section": "Refunds", "old_text": "30 days", "new_text": "14 days", "old_anchor": "30", "new_anchor": "14"}
        body = {"choices": [{"message": {"content": '{"question":"Is it 14 days?"}'}}]}
        with patch("revprobe.llm.urlopen", return_value=FakeReply(json.dumps(body).encode())):
            with self.assertRaises(ValueError):
                improve_question(case, model="local", api_base="http://localhost:11434/v1")


if __name__ == "__main__":
    unittest.main()
