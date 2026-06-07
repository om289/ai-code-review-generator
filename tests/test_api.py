"""Tests for the Flask web and API routes."""

import unittest
from unittest.mock import patch, MagicMock

from app import create_app


class TestWebRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_index_get(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"AI Code Review", resp.data)

    def test_health_endpoint(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("prompt_version", data)

    def test_metrics_endpoint(self):
        resp = self.client.get("/metrics")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("runs", data)
        self.assertIn("feedback", data)

    def test_api_runs_empty(self):
        resp = self.client.get("/api/runs")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("runs", data)

    def test_api_run_not_found(self):
        resp = self.client.get("/api/runs/nonexistent")
        self.assertEqual(resp.status_code, 404)

    def test_export_not_found(self):
        resp = self.client.get("/export/nonexistent.txt")
        self.assertEqual(resp.status_code, 404)

    def test_api_review_empty_body(self):
        resp = self.client.post(
            "/api/review",
            json={"diff_text": ""},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_api_feedback_invalid_run(self):
        resp = self.client.post(
            "/api/feedback",
            json={"run_id": "fake", "rating": 5},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
