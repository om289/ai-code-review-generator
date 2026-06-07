"""Tests for the code review pipeline — models, prompts, and mocked LLM."""

import unittest
from unittest.mock import MagicMock, patch

from src.models import AppError, ReviewRequest
from src.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_review_prompt
from src.config import Settings


class TestReviewRequest(unittest.TestCase):
    def test_valid_diff(self):
        req = ReviewRequest(diff_text="+ added line\n- removed line")
        req.validate()

    def test_empty_diff_raises(self):
        req = ReviewRequest(diff_text="")
        with self.assertRaises(AppError):
            req.validate()

    def test_whitespace_only_raises(self):
        req = ReviewRequest(diff_text="   \n\n  ")
        with self.assertRaises(AppError):
            req.validate()

    def test_oversized_diff_raises(self):
        req = ReviewRequest(diff_text="x" * 31000, max_chars=30000)
        with self.assertRaises(AppError) as ctx:
            req.validate()
        self.assertIn("too long", str(ctx.exception))


class TestPrompts(unittest.TestCase):
    def test_prompt_version_exists(self):
        self.assertTrue(PROMPT_VERSION.startswith("code-review-"))

    def test_system_prompt_contains_severity(self):
        self.assertIn("P0", SYSTEM_PROMPT)
        self.assertIn("P1", SYSTEM_PROMPT)

    def test_build_review_prompt_includes_diff(self):
        result = build_review_prompt("+ new line")
        self.assertIn("+ new line", result)

    def test_build_review_prompt_truncates(self):
        long_diff = "x" * 1000
        result = build_review_prompt(long_diff, max_chars=100)
        self.assertIn("truncated", result)
        self.assertIn("x" * 100, result)


class TestConfig(unittest.TestCase):
    @patch.dict("os.environ", {"AI_API_KEY": "test-key-123"}, clear=False)
    def test_has_api_key_true(self):
        cfg = Settings()
        self.assertTrue(cfg.has_api_key)

    @patch.dict("os.environ", {"AI_API_KEY": ""}, clear=False)
    def test_has_api_key_false_empty(self):
        cfg = Settings()
        self.assertFalse(cfg.has_api_key)

    @patch.dict("os.environ", {"AI_API_KEY": "your_api_key_here"}, clear=False)
    def test_has_api_key_false_placeholder(self):
        cfg = Settings()
        self.assertFalse(cfg.has_api_key)

    def test_validate_warns_without_key(self):
        with patch.dict("os.environ", {"AI_API_KEY": ""}, clear=False):
            cfg = Settings()
            warnings = cfg.validate()
            self.assertTrue(any("AI_API_KEY" in w for w in warnings))


class TestMockedLLMClient(unittest.TestCase):
    @patch("src.llm_client.OpenAI")
    def test_generate_review_returns_content(self, mock_openai_cls):
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = "Summary:\n- No issues found."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        with patch.dict("os.environ", {"AI_API_KEY": "test-key"}, clear=False):
            from src.llm_client import ReviewClient
            cfg = Settings()
            client = ReviewClient(cfg)
            review, model = client.generate_review("+ new line")

        self.assertIn("No issues found", review)
        self.assertTrue(model)


if __name__ == "__main__":
    unittest.main()
